"""Evaluate frozen C++ models on held-out data, legal children, and actual search leaves."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

import numpy as np

from diagnostic_metrics import (MODES, clipping_pairs, corrections, distribution,
                                rank_metrics, ranking_summary, stability)
from stockfish_labels import Stockfish


def full_fen(fen):
    return fen + " 0 1" if len(fen.split()) == 4 else fen


def key(fen):
    # Conservative identity: retain en-passant and castling rights; ignore clocks.
    return " ".join(fen.split()[:4])


def native(executable, fens, options=()):
    result = subprocess.run([str(executable), *map(str, options)], input="\n".join(map(full_fen, fens))+"\n",
                            capture_output=True, text=True, check=True)
    return [json.loads(line) for line in result.stdout.splitlines()]


def atomic_text(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent, prefix=path.name+".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(content)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def percentage_boundary(values):
    x = np.asarray(values)
    if not len(x):
        return {"count": 0, "negative_percent": None, "positive_percent": None, "either_percent": None}
    return {"count": len(x), "negative_percent": float(100*np.mean(x <= -1500)),
            "positive_percent": float(100*np.mean(x >= 1500)),
            "either_percent": float(100*np.mean(abs(x) >= 1500))}


def markdown(report):
    lines = ["# Frozen V2 evaluator diagnostics", "", report["interpretation"], "",
             "No training or model changes. All scores are White centipawns. Percentages use 0–100; ranking accuracy uses 0–1.",
             "", "## A. Global held-out label error", "",
             "Full test split; labels are already clipped at ±1500. Raw and deployed scores are reported separately.", "",
             "| Evaluator | MAE cp | RMSE cp |", "|---|---:|---:|"]
    for mode, stats in report["global_error"].items():
        lines.append(f"| {mode} | {stats['mae']:.2f} | {stats['rmse']:.2f} |")
    rank = report["ranking"]
    lines += ["", "## B. Sibling move ranking", "", rank["note"], "",
              f"Parents sampled: {rank['sampled_parents']}; complete nonterminal cp-labelled sets: {rank['complete_cp_parents']}; "
              f"cached child labels: {rank['cached_children']} / {rank['total_children']}; mate-containing sets excluded: {rank['mate_parents']}; forced-move parents excluded: {rank['forced_move_parents']}.", ""]
    if rank["complete_cp_parents"]:
        lines += ["| Evaluator | Top-1 | Target-best in top-3 | Pairwise | Spearman | Regret cp |", "|---|---:|---:|---:|---:|---:|"]
        for mode, m in rank["evaluators"].items():
            def fmt(v): return "n/a" if v is None else f"{v:.4f}"
            lines.append("| " + " | ".join([mode]+[fmt(m[k]) for k in ("top1", "top3_contains_target_best", "pairwise_accuracy", "spearman", "regret_cp")])+" |")
    else:
        lines += ["**Ranking unavailable:** no complete, trusted child-label sets. Pass `--stockfish` to measure it; no labels were invented."]
    lines += ["", "Top-1 accepts any target-best tie. Top-3 means at least one target-best child is among the evaluator's first three. "
              "UCI move order breaks prediction ties; JSON also reports uniform tie expectations. Pairwise excludes target ties, "
              "credits predicted ties 0.5, and averages per parent. Spearman uses average ranks, excluding constant rankings. "
              "All metrics optimize for the parent side; regret is nonnegative.", "", "## C. Parent–child stability", "",
              "Deltas are child minus parent in White cp. Captures can legitimately change material; this is not an accuracy metric.", "",
              "| Evaluator/group | Edges | Median abs | p90 abs | p95 abs | p99 abs | Sign flips % | >300 cp % |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for mode in MODES:
        for group in ("capture", "quiet"):
            m = report["stability"][mode][group]
            if m["count"]:
                lines.append(f"| {mode}/{group} | {m['count']} | "+" | ".join(f"{m[k]:.2f}" for k in ("abs_p50", "abs_p90", "abs_p95", "abs_p99", "sign_flip_percent", "abs_over_300_percent"))+" |")
    lines += ["", "## D. Residual corrections on the test split", "",
              "Both raw residual and deployed Hybrid−Classic are measured; the latter includes clipping and rounding.", "",
              "| Correction / Classic absolute range | Mean | Std | Median abs | p95 abs | Sign flips % | Exceeds Classic magnitude % |",
              "|---|---:|---:|---:|---:|---:|---:|"]
    for kind, groups in report["corrections"].items():
        for group, m in groups.items():
            if m["count"]:
                lines.append(f"| {kind}/{group} | "+" | ".join(f"{m[k]:.2f}" for k in ("mean", "std", "abs_p50", "abs_p95", "sign_flip_percent", "exceeds_classic_magnitude_percent"))+" |")
    lines += ["", "## E. Clipping", "", "| Population | At/beyond ±1500 % |", "|---|---:|"]
    for name, m in report["clipping"]["boundaries"].items():
        value = "n/a" if m["either_percent"] is None else f"{m['either_percent']:.3f}"
        lines.append(f"| {name} | {value} |")
    lines += ["", "| Raw evaluator / tolerance | New tied pairs % | Affected parents % |", "|---|---:|---:|"]
    for name, m in report["clipping"]["sibling_ties"].items():
        lines.append(f"| {name} | {m['pair_percent']} | {m['affected_parent_percent']} |")
    lines += ["", "A new tie requires raw separation greater than the tolerance and separation after clipping no greater than it. "
              "Tolerance 0 is exact, 5 cp is near. Rounding is excluded from this attribution. Boundary labels cannot distinguish "
              "naturally exact ±1500 values from censored values, and original unbounded targets cannot be recovered.", "",
              "## F. Actual depth-3 search evaluations", "", report["leaves"]["note"], "",
              "| Search evaluator | Events seen | Sampled | Mean ply | Captures % | Classic median abs | ML median abs | Hybrid median abs |",
              "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for mode, m in report["leaves"]["by_search_mode"].items():
        if m["selected"]:
            lines.append(f"| {mode} | {m['events_seen']} | {m['selected']} | {m['ply']['mean']:.2f} | {m['capture_percent']:.2f} | "
                         + " | ".join(f"{m['scores'][s]['abs_p50']:.2f}" for s in MODES)+" |")
    lines += ["", "Full JSON contains all requested thresholds/percentiles, raw/unclipped outputs, leaf score/correction statistics, "
              "search summaries, model IDs, dataset hashes, and sample indices. The companion `.samples.jsonl` retains every sampled child and leaf.",
              "", "## Interpretation and alpha pilots", "", report["interpretation"], "",
              "Existing tournament outcomes are recorded in JSON with their finite-opening bootstrap uncertainty. "
              "Global MAE, local stability, and clipping alone do not identify the cause of weaker play. "
              "Use the paired alpha commands in `DIAGNOSTICS.md`; do not select a final alpha solely on these 16 openings.", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("ml/data/lichess_250k_v2.npz"))
    parser.add_argument("--engine", type=Path, default=Path("build/Release/ChessAI_diagnostics.exe"))
    parser.add_argument("--parents", type=int, default=500)
    parser.add_argument("--leaf-roots", type=int, default=6)
    parser.add_argument("--leaf-samples", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--stockfish", type=Path)
    parser.add_argument("--stockfish-depth", type=int, default=12)
    parser.add_argument("--output", type=Path, default=Path("benchmarks/diagnostic_report.json"))
    args = parser.parse_args()
    if min(args.parents, args.leaf_samples, args.stockfish_depth) < 1 or args.leaf_roots < 0 or args.seed < 0:
        parser.error("Counts/depth must be positive; leaf-roots and seed nonnegative")
    with np.load(args.data, allow_pickle=False) as data:
        fens, y, split = data["fen"], data["y"].astype(float), data["split"]
        metadata = json.loads(str(data["metadata"]))
    if metadata.get("target_perspective") != "white" or metadata.get("clip_cp") != 1500:
        raise ValueError("Expected White cp dataset clipped at 1500")
    test = np.flatnonzero(split == 2)
    if not len(test):
        raise ValueError("Empty test split")
    selected = np.random.default_rng(args.seed).permutation(test)[:args.parents]
    print(f"Global evaluation: {len(test)} held-out positions", flush=True)
    global_records = native(args.engine, fens[test])
    rows = [r["parent"] for r in global_records if r["type"] == "parent"]
    errors = {}
    for mode in (*MODES, "direct_raw", "hybrid_raw"):
        delta = np.array([r[mode] for r in rows])-y[test]
        errors[mode] = {"count": len(delta), "mae": float(abs(delta).mean()), "rmse": float(np.sqrt(np.mean(delta**2)))}
    print(f"Children: {len(selected)} parents; depth-3 leaf roots: {min(args.leaf_roots, len(selected))}", flush=True)
    records = native(args.engine, fens[selected], ("--children", "--leaf-roots", args.leaf_roots,
                                               "--leaf-samples", args.leaf_samples, "--seed", args.seed))
    parents = [r for r in records if r["type"] == "parent"]
    # Existing local labels only. Keep conflicts unavailable rather than arbitrarily picking one.
    cache, conflicts = {}, set()
    for fen, value in zip(fens, y):
        k = key(fen)
        if k in cache and cache[k] != value:
            conflicts.add(k)
        cache[k] = float(value)
    for k in conflicts:
        del cache[k]
    sf = Stockfish(args.stockfish, args.stockfish_depth) if args.stockfish else None
    rank = {"sampled_parents": len(parents), "total_children": 0, "cached_children": 0, "complete_cp_parents": 0,
            "mate_parents": 0, "incomplete_parents": 0, "terminal_parents": 0, "forced_move_parents": 0,
            "source": sf.metadata if sf else {"dataset": str(args.data), "labels": "clipped White cp"},
            "note": "With --stockfish, every child uses that engine at identical depth (no mixed label sources). Otherwise only complete local cached sets are ranked. "
                    "Cached FEN matching uses the first four fields, retains en-passant, ignores clocks/history; coverage is conservative. "
                    "Parents with any mate score or missing label are excluded from cp ranking/regret; mates are never mapped to invented centipawns."}
    metrics = {m: [] for m in MODES}
    sf_cache = {}
    try:
        for index, row in enumerate(parents):
            children = sorted(row["children"], key=lambda c: c["move"])
            rank["total_children"] += len(children)
            rank["cached_children"] += sum(key(c["fen"]) in cache for c in children)
            if not children:
                rank["terminal_parents"] += 1
                continue
            for child in children:
                if sf:
                    if child["fen"] not in sf_cache:
                        sf_cache[child["fen"]] = sf.evaluate(child["fen"])
                    child["target"] = sf_cache[child["fen"]]
                else:
                    value = cache.get(key(child["fen"]))
                    child["target"] = None if value is None else {"cp_white": value}
            if any(c["target"] is None for c in children):
                rank["incomplete_parents"] += 1
                continue
            if any("mate_white" in c["target"] for c in children):
                rank["mate_parents"] += 1
                continue
            if len(children) == 1:
                rank["forced_move_parents"] += 1
                continue
            rank["complete_cp_parents"] += 1
            targets = [c["target"]["cp_white"] for c in children]
            for mode in MODES:
                metrics[mode].append(rank_metrics([c[mode] for c in children], targets, row["parent"]["side"]))
            if sf and (index+1) % 10 == 0:
                print(f"Trusted child labels: {index+1}/{len(parents)} parents", flush=True)
    finally:
        if sf:
            sf.close()
    rank["evaluators"] = {m: ranking_summary(values) for m, values in metrics.items()}
    boundaries = {name+"_labels": percentage_boundary(y[split == i]) for i, name in enumerate(("train", "validation", "test"))}
    boundaries.update({m: percentage_boundary([r[m] for r in rows]) for m in ("ml", "hybrid", "direct_raw", "hybrid_raw")})
    leaves = {"note": "Uniform reservoir over static evaluation events per search evaluator, including quiescence stand-pat, not terminal mate scores. "
              "Repeated positions are retained; more expensive roots contribute more events. Independent fresh TT per root/mode. "
              "Root ordering is a seeded random held-out subset. No trusted leaf targets are implied. Incoming -1 denotes root/unknown.",
              "by_search_mode": {}, "searches": [r for r in records if r["type"] == "search"]}
    for summary in (r for r in records if r["type"] == "leaf_summary"):
        mode = summary["mode"]
        sample = [r for r in records if r["type"] == "leaf" and r["search_mode"] == mode]
        leaves["by_search_mode"][mode] = {**summary, "ply": distribution([r["ply"] for r in sample]),
            "capture_percent": 100*sum(r["incoming"] == 1 for r in sample)/len(sample) if sample else None,
            "quiet_count": sum(r["incoming"] == 0 for r in sample), "unknown_count": sum(r["incoming"] < 0 for r in sample),
            "white_to_move_count": sum(r["side"] == "w" for r in sample),
            "scores": {m: distribution([r[m] for r in sample]) for m in (*MODES, "direct_raw", "residual_raw", "hybrid_raw")},
            "corrections": corrections(sample),
            "clipping": {m: percentage_boundary([r[m] for r in sample]) for m in ("ml", "hybrid")} if sample else {}}
    tournaments = {}
    for path in sorted(Path("benchmarks").glob("*_depth3_32.json")):
        result = json.loads(path.read_text(encoding="utf-8"))
        tournaments[path.name] = {k: result[k] for k in ("config", "models", "summary")}
    report = {"format_version": 1, "config": {k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()},
              "dataset_sha256": hashlib.sha256(args.data.read_bytes()).hexdigest(),
              "engine_sha256": hashlib.sha256(args.engine.read_bytes()).hexdigest(),
              "models": global_records[0], "test_count": len(test), "parent_dataset_indices": selected.tolist(),
              "global_error": errors, "ranking": rank, "stability": stability(parents), "corrections": corrections(rows),
              "clipping": {"boundaries": boundaries, "sibling_ties": {f"{m}_tolerance_{tol}": clipping_pairs(parents, m, tol)
                           for m in ("direct_raw", "hybrid_raw") for tol in (0, 5)}},
              "leaves": leaves, "existing_tournaments": tournaments,
              "interpretation": "The frozen neural models fit clipped held-out Stockfish labels better than Classic, while the supplied depth-3 paired matches favor Classic. "
              "These are different measurements. Correction magnitudes, local changes and clipping are diagnostic observations, not proof of the cause. "
              + ("Sibling ranking is unavailable without complete trusted child labels." if not rank["complete_cp_parents"] else "Sibling ranking results apply only to the reported complete cp-labelled subset and target engine/settings.")}
    atomic_text(args.output.with_suffix(".samples.jsonl"), "\n".join(json.dumps(r, allow_nan=False) for r in records)+"\n")
    atomic_text(args.output, json.dumps(report, indent=2, allow_nan=False)+"\n")
    atomic_text(args.output.with_suffix(".md"), markdown(report))
    print(f"Wrote {args.output} and {args.output.with_suffix('.md')}")


if __name__ == "__main__":
    main()
