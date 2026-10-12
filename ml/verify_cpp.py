"""Compare actual C++ features and (optionally) predictions against Python."""
import argparse
import json
import subprocess
import numpy as np
from features import START_FEN, features_from_fen
from make_example import example_records


def test_fens():
    fens = [START_FEN, START_FEN.replace("RNBQKBNR", "RNB1KBNR"),
            START_FEN.replace("rnbqkbnr", "rnb1kbnr"),
            "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
            "4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1"]
    for side in ["w", "b"]:
        for mask in range(16):
            rights = "".join(c for i, c in enumerate("KQkq") if mask & (1 << i)) or "-"
            fens.append(f"r3k2r/8/8/8/8/8/8/R3K2R {side} {rights} - 0 1")
    fens.extend(record["fen"] + " 0 1" for record in example_records(200))
    return fens


def run_tool(path, operation, fens):
    result = subprocess.run([path, operation], input="\n".join(fens) + "\n",
                            text=True, capture_output=True, check=True)
    return result.stdout.splitlines()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tool", required=True)
    parser.add_argument("--checkpoint")
    parser.add_argument("--require-sanity", action="store_true", help="Quality gate for a real trained model")
    args = parser.parse_args()
    fens = test_fens()
    expected = np.stack([features_from_fen(fen) for fen in fens])
    actual = np.array([[float(v) for v in line.split()] for line in run_tool(args.tool, "features", fens)])
    np.testing.assert_array_equal(actual, expected)
    print(f"Exact Python/C++ feature parity: {len(fens)} positions x 773 features")
    if args.checkpoint:
        import torch
        from model import load_checkpoint, TARGET_SCALE
        from train_evaluator import sanity_checks
        model, checkpoint = load_checkpoint(args.checkpoint)
        with torch.inference_mode():
            cp = model(torch.from_numpy(expected).float()).numpy() * TARGET_SCALE
        cpp = np.array([int(line) for line in run_tool(args.tool, "predict", fens)])
        error = np.max(np.abs(cpp - np.clip(cp, -1500, 1500)))
        if error > 1.0:
            raise AssertionError(f"C++/PyTorch maximum difference {error} cp > 1 cp")
        print(f"Inference parity: max difference {error:.6f} cp (includes integer rounding)")
        sanity = sanity_checks(model, torch.device("cpu"))
        print(json.dumps(sanity, indent=2))
        if args.require_sanity and not all(v for v in sanity.values() if isinstance(v, bool)):
            raise AssertionError("Model failed chess sanity gate")
    elif args.require_sanity:
        parser.error("--require-sanity needs --checkpoint")


if __name__ == "__main__":
    main()
