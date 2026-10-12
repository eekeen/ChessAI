"""Upgrade an existing sampled NPZ without resampling or reading the dump."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import numpy as np
from features_v2 import extend_features, SCHEMA_HASH
from preprocess_dataset import write_dataset


def classic_scores(tool, fens):
    # One process for the complete batch. communicate drains pipes without deadlock.
    normalized = [str(fen) + (" 0 1" if len(str(fen).split()) == 4 else "") for fen in fens]
    result = subprocess.run([str(tool), "classic"], input="\n".join(normalized) + "\n",
                            text=True, capture_output=True, check=True)
    scores = np.asarray([int(line) for line in result.stdout.splitlines()], dtype=np.float32)
    if len(scores) != len(fens):
        raise ValueError("C++ helper returned the wrong number of Classic scores")
    return scores


def prepare(source, output, tool):
    if Path(source).resolve() == Path(output).resolve():
        raise ValueError("V2 output must not overwrite the V1 dataset")
    with np.load(source, allow_pickle=False) as data:
        arrays = {key: data[key] for key in data.files if key != "metadata"}
        metadata = json.loads(str(data["metadata"]))
    if metadata["feature_version"] != 1 or metadata["target_perspective"] != "white":
        raise ValueError("Expected White-perspective V1 dataset")
    if arrays["X"].shape != (len(arrays["y"]), 773):
        raise ValueError("Invalid V1 feature dimensions")
    print(f"Computing Classic targets in one C++ batch: {len(arrays['y']):,} positions", flush=True)
    arrays["classic"] = classic_scores(tool, arrays["fen"])
    arrays["residual"] = arrays["y"] - arrays["classic"]
    arrays["X"] = extend_features(arrays["X"])
    with open(source, "rb") as file:
        source_hash = hashlib.file_digest(file, "sha256").hexdigest()
    with open(tool, "rb") as file:
        tool_hash = hashlib.file_digest(file, "sha256").hexdigest()
    metadata.update(feature_version=2, schema_sha256=SCHEMA_HASH, source_dataset_sha256=source_hash,
                    classic_tool_sha256=tool_hash, classic_tool=str(Path(tool).resolve()),
                    residual_definition="stockfish clipped White cp minus exact Classic White cp")
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    write_dataset(output, arrays, metadata)
    print(f"Wrote {output}; preserved original rows, labels and splits")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", default="ml/data/lichess_250k.npz")
    parser.add_argument("--output", default="ml/data/lichess_250k_v2.npz")
    parser.add_argument("--tool", default="build/Release/eval_tool.exe")
    args = parser.parse_args()
    prepare(args.data, args.output, args.tool)
