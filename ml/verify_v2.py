"""Shared-schema, feature, target and C++/PyTorch V2 inference validation."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import numpy as np
import torch
from features import START_FEN
from features_v2 import features_from_fen, extend_features, INPUT_SIZE
from model_v2 import load_checkpoint, TARGET_SCALE
from prepare_v2 import classic_scores
from verify_cpp import test_fens, run_tool
from material_sanity import cases


def verify(tool, direct=None, residual=None, data=None):
    subprocess.run([sys.executable, str(Path(__file__).with_name("generate_feature_schema.py")), "--check"], check=True)
    start = features_from_fen(START_FEN)
    np.testing.assert_array_equal(start[773:], [1] * 10 + [0, 1, 1, 1, 0, 0])
    missing = features_from_fen(START_FEN.replace("RNBQKBNR", "RNB1KBNR"))
    expected = start[773:].copy()
    expected[4], expected[10], expected[11] = 0, -900 / 4000, 20 / 24
    np.testing.assert_allclose(missing[773:], expected, atol=1e-7)
    # Hand-checked isolated piece counts exercise every new count and value.
    for piece, type_index, value in zip("PNBRQ", range(5), [100, 320, 330, 500, 900]):
        for white in (True, False):
            fen = f"4k3/8/8/8/8/{piece if white else piece.lower()}7/8/4K3 w - - 0 1"
            vector = features_from_fen(fen)
            offset = 0 if white else 5
            assert vector[773 + offset + type_index] == 1 / [8, 2, 2, 2, 1][type_index]
            np.testing.assert_allclose(vector[783], (1 if white else -1) * value / 4000, atol=1e-7)
    assert features_from_fen("4k3/8/8/8/8/BB6/8/4K3 w - - 0 1")[785] == 1
    assert features_from_fen("4k3/8/8/8/8/bb6/8/4K3 w - - 0 1")[786] == 1
    fens = test_fens() + [item["fen"] for item in cases()]
    fens += ["2k5/8/8/8/8/8/8/2K5 w - - 0 1", "6k1/8/8/8/8/8/8/6K1 b - - 0 1",
             "4k3/qqqqqqqq/8/8/8/8/QQQQQQQQ/4K3 w - - 0 1"]
    for fen in fens[-3:-1]:
        np.testing.assert_array_equal(features_from_fen(fen)[787:], [1, 1])
    assert features_from_fen(fens[-1])[784] == 1  # promoted material phase saturates
    expected = np.stack([features_from_fen(fen) for fen in fens])
    actual = np.asarray([[float(value) for value in line.split()] for line in run_tool(tool, "features-v2", fens)], dtype=np.float32)
    np.testing.assert_array_equal(actual, expected)
    print(f"Exact float32 feature parity: {len(fens)} positions x {INPUT_SIZE}; all scalar features covered")
    classic = classic_scores(tool, fens)
    for checkpoint_path, kind in [(direct, "direct"), (residual, "residual")]:
        if not checkpoint_path:
            continue
        model, checkpoint = load_checkpoint(checkpoint_path)
        assert checkpoint["kind"] == kind
        with torch.inference_mode():
            prediction = model(torch.from_numpy(expected)).numpy() * TARGET_SCALE
        cpp = np.asarray([float(v) for v in run_tool(tool, f"{kind}-v2", fens)])
        np.testing.assert_allclose(cpp, prediction, rtol=0, atol=0.02)
        print(f"{kind} raw inference parity: max error {np.max(abs(cpp - prediction)):.6f} cp")
        if kind == "residual":
            hybrid = np.asarray([int(v) for v in run_tool(tool, "hybrid-v2", fens)])
            assert np.max(abs(hybrid - np.clip(classic + prediction, -1500, 1500))) <= 0.52
            print("Hybrid = Classic + residual, then clipped/rounded: parity passed")
            alpha = float(subprocess.check_output([tool, "production-alpha"], text=True))
            assert alpha == .25
            production = np.asarray([int(v) for v in run_tool(tool, "hybrid-production", fens)])
            assert np.max(abs(production - np.clip(classic + alpha * prediction, -1500, 1500))) <= .52
            print("Production Hybrid = Classic + 0.25 residual: parity passed")
    if data:
        with np.load(data) as dataset:
            indices = np.linspace(0, len(dataset["y"]) - 1, 128, dtype=int)
            fens = dataset["fen"][indices]
            np.testing.assert_array_equal(classic_scores(tool, fens), dataset["classic"][indices])
            np.testing.assert_array_equal(dataset["residual"], dataset["y"] - dataset["classic"])
            np.testing.assert_array_equal(extend_features(dataset["X"][indices, :773]), dataset["X"][indices])
        print("Stored Classic/residual targets and V2 features verified")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tool", default="build/Release/eval_tool.exe")
    parser.add_argument("--direct")
    parser.add_argument("--residual")
    parser.add_argument("--data")
    args = parser.parse_args()
    verify(args.tool, args.direct, args.residual, args.data)
