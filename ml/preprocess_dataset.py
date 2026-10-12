"""Stream official Lichess JSONL.zst; stratified reservoir, disk-backed dedup."""
import argparse
from collections import Counter
from contextlib import closing
import io
import json
from itertools import islice
import os
from pathlib import Path
import random
import sqlite3
import tempfile

import numpy as np
import zstandard as zstd

from features import FEATURE_VERSION, features_from_fen, parse_fen

EDGES = [-800, -300, -100, 100, 300, 800]


def report_progress(stats, reservoirs, overflow, args):
    counts = [len(bucket) for bucket in reservoirs]
    print(f"Read: {stats['positions_read']:,} / {args.max_records:,}\n"
          f"Unique usable: {stats['positions_accepted']:,}\n"
          f"Selected/reservoir size: {sum(counts):,} / {args.samples:,}\n"
          f"Per-bin reservoir counts: {counts}\n"
          f"Overflow reserve for redistribution: {len(overflow):,}", flush=True)


def write_dataset(output, arrays, metadata):
    """Stage both files before publishing; never expose a half-written NPZ.

    Each replacement is atomic. The NPZ's embedded metadata is authoritative
    if interruption occurs between the two final replacements.
    """
    staged = []
    try:
        for destination in (output, output.with_suffix(".metadata.json")):
            with tempfile.NamedTemporaryFile(dir=output.parent, prefix=f".{output.name}.",
                                             suffix=".tmp", delete=False) as file:
                staged.append((Path(file.name), destination))
        with staged[0][0].open("wb") as file:
            np.savez_compressed(file, **arrays, metadata=json.dumps(metadata))
            file.flush()
            os.fsync(file.fileno())
        staged[1][0].write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        for temporary, destination in staged:
            os.replace(temporary, destination)
    finally:
        for temporary, _ in staged:
            temporary.unlink(missing_ok=True)


def score_bin(score):
    return int(np.searchsorted(EDGES, score, side="right"))


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and np.isfinite(value)


def extract_record(record, perspective="white"):
    if not isinstance(record, dict):
        raise ValueError("Expected object")
    _, turn, _, fen = parse_fen(record.get("fen"))
    evaluations = record.get("evals")
    if not isinstance(evaluations, list):
        raise ValueError("Missing evals array")
    candidates = []
    for evaluation in evaluations:
        if not isinstance(evaluation, dict):
            continue
        depth, nodes = evaluation.get("depth", 0), evaluation.get("knodes", 0)
        pvs = evaluation.get("pvs")
        if not number(depth) or depth < 0 or not isinstance(pvs, list) or not pvs:
            continue
        # Only PV1 represents the best move; a lower PV is not a substitute.
        pv = pvs[0]
        if not isinstance(pv, dict):
            continue
        if number(pv.get("mate")):
            mate = pv["mate"]
            # Mate zero loses for the side currently to move.
            cp = (1500 if turn == "b" else -1500) if mate == 0 else (1500 if mate > 0 else -1500)
            if perspective == "stm" and mate != 0 and turn == "b":
                cp = -cp
        elif number(pv.get("cp")):
            cp = pv["cp"]
            if perspective == "stm" and turn == "b":
                cp = -cp
        else:
            continue
        candidates.append(((depth, nodes if number(nodes) else 0), float(np.clip(cp, -1500, 1500))))
    if not candidates:
        raise ValueError("No usable primary evaluation")
    strength, cp = max(candidates, key=lambda item: item[0])
    return fen, cp, strength[0]


def preprocess(args):
    if args.max_records is None:
        args.max_records = max(args.samples * 8, args.samples)
    if args.samples < 10 or args.max_records < 1:
        raise ValueError("samples must be >=10 and max-records must be positive")
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)
    quotas = [args.samples // 7 + (i < args.samples % 7) for i in range(7)]
    reservoirs = [[] for _ in range(7)]
    # A second uniform reservoir retains rejected/evicted primary samples.
    # It guarantees enough distinct replacements without storing the whole prefix.
    overflow = []
    overflow_seen = 0
    overflow_rng = random.Random(args.seed)
    seen_bins = [0] * 7
    stats = Counter(positions_read=0, positions_accepted=0, malformed_records=0, duplicates=0)
    # Exact keys live on disk, not in a Python set growing with the full corpus.
    with tempfile.TemporaryDirectory(dir=args.dedup_dir) as scratch:
        with closing(sqlite3.connect(str(Path(scratch) / "seen.sqlite"))) as db:
            db.execute("PRAGMA journal_mode=OFF")
            db.execute("PRAGMA synchronous=OFF")
            db.execute("PRAGMA cache_size=-32768")
            db.execute("CREATE TABLE seen (key TEXT PRIMARY KEY) WITHOUT ROWID")
            with open(args.input, "rb") as source, zstd.ZstdDecompressor().stream_reader(source) as stream:
                with io.TextIOWrapper(stream, encoding="utf-8", errors="replace") as lines:
                    report_progress(stats, reservoirs, overflow, args)
                    progress_interval = min(100000, max(1, args.max_records // 10))
                    for line in islice(lines, args.max_records):
                        # Report even if the previous batch was all malformed/duplicate.
                        if stats["positions_read"] and stats["positions_read"] % progress_interval == 0:
                            report_progress(stats, reservoirs, overflow, args)
                            db.commit()
                        stats["positions_read"] += 1
                        try:
                            fen, cp, depth = extract_record(json.loads(line), args.score_perspective)
                        except (ValueError, TypeError, OverflowError):
                            stats["malformed_records"] += 1
                            continue
                        # Ignore counters AND ep in the dedup key: v1 cannot see either.
                        key = " ".join(fen.split()[:3])
                        cursor = db.execute("INSERT OR IGNORE INTO seen VALUES (?)", (key,))
                        if cursor.rowcount == 0:
                            stats["duplicates"] += 1
                            continue
                        stats["positions_accepted"] += 1
                        index = score_bin(cp)
                        seen_bins[index] += 1
                        bucket = reservoirs[index]
                        row = (fen, cp, depth)
                        if len(bucket) < quotas[index]:
                            bucket.append(row)
                        else:
                            slot = rng.randrange(seen_bins[index])
                            if slot < quotas[index]:
                                row, bucket[slot] = bucket[slot], row
                            overflow_seen += 1
                            if len(overflow) < args.samples:
                                overflow.append(row)
                            else:
                                extra_slot = overflow_rng.randrange(overflow_seen)
                                if extra_slot < args.samples:
                                    overflow[extra_slot] = row
    shortfall = args.samples - sum(len(bucket) for bucket in reservoirs)
    extras = overflow_rng.sample(overflow, min(shortfall, len(overflow)))
    for row in extras:
        reservoirs[score_bin(row[1])].append(row)
    report_progress(stats, reservoirs, [], args)
    rows = [row for bucket in reservoirs for row in bucket]
    if len(rows) < 10:
        raise ValueError(f"Only {len(rows)} samples; need at least 10 for three splits")
    # Stratified split, then ensure every split is nonempty for tiny smoke inputs.
    split_ids = []
    for bucket in reservoirs:
        n = len(bucket)
        indices = list(range(n))
        rng.shuffle(indices)
        val_n = test_n = int(n * 0.1)
        labels = [0] * n
        for i in indices[:val_n]:
            labels[i] = 1
        for i in indices[val_n:val_n + test_n]:
            labels[i] = 2
        split_ids.extend(labels)
    for label in (1, 2):
        if label not in split_ids:
            split_ids[split_ids.index(0)] = label
    order = list(range(len(rows)))
    rng.shuffle(order)
    rows = [rows[i] for i in order]
    splits = np.asarray([split_ids[i] for i in order], dtype=np.uint8)
    x = np.stack([features_from_fen(row[0]) for row in rows])
    y = np.asarray([row[1] for row in rows], dtype=np.float32)
    source = Path(args.input).resolve()
    metadata = dict(vars(args), source=str(source), source_bytes=source.stat().st_size,
                    source_mtime_ns=source.stat().st_mtime_ns, feature_version=FEATURE_VERSION,
                    target_perspective="white", clip_cp=1500, split_names=["train", "validation", "test"],
                    dedup_key="piece placement, turn, castling (first usable record wins)",
                    bin_edges=EDGES, bin_boundary="left inclusive, right exclusive",
                    stats=dict(stats), sampled_bins=[len(b) for b in reservoirs], unique_bins=seen_bins,
                    initial_bin_quotas=quotas, redistributed_samples=len(extras),
                    selected=len(rows), minimum=float(y.min()), maximum=float(y.max()),
                    mean=float(y.mean()), standard_deviation=float(y.std()),
                    split_counts=np.bincount(splits, minlength=3).tolist())
    write_dataset(output, dict(X=x, y=y, split=splits, fen=np.array([r[0] for r in rows]),
                              depth=np.array([r[2] for r in rows])), metadata)
    print(f"Completed: {output}\n"
          f"Total raw records read: {stats['positions_read']:,}\n"
          f"Unique usable records: {stats['positions_accepted']:,}\n"
          f"Final selected samples: {len(rows):,}\n"
          f"Per-bin counts: {metadata['sampled_bins']}\n"
          f"Redistributed samples: {len(extras):,}\n"
          f"Duplicates: {stats['duplicates']:,}\n"
          f"Malformed records: {stats['malformed_records']:,}\n"
          f"Evaluation min/max/mean/std (cp): {y.min():.2f} / {y.max():.2f} / {y.mean():.2f} / {y.std():.2f}\n"
          f"Train/validation/test sizes: {metadata['split_counts']}")
    if len(rows) < args.samples:
        print("Not enough unique usable records within the scan limit; returning all available samples.")
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--samples", type=int, default=250000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-records", type=int, default=None,
                        help="Positive raw-record scan limit (default: max(samples * 8, samples))")
    parser.add_argument("--dedup-dir", help="Directory for temporary SQLite index (potentially large)")
    parser.add_argument("--score-perspective", choices=["white", "stm"], default="white",
                        help="Official Lichess scores are white-relative; stm only for other converted inputs")
    try:
        preprocess(parser.parse_args())
    except KeyboardInterrupt:
        parser.exit(130, "\nPreprocessing interrupted; no partially written dataset was published.\n")


if __name__ == "__main__":
    main()
