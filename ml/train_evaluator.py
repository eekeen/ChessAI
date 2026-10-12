"""Train a small position evaluator; select by validation MSE, test once."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import random

import numpy as np
import torch
from torch.utils.data import DataLoader, TensorDataset

from features import FEATURE_VERSION, START_FEN, features_from_fen
from model import EvaluatorNet, MODEL_VERSION, TARGET_SCALE, load_checkpoint


def metrics(prediction, target):
    error = prediction.astype(np.float64) - target
    return {"count": len(error), "loss": float(np.mean((error / TARGET_SCALE) ** 2)),
            "mae_cp": float(np.mean(np.abs(error))), "rmse_cp": float(np.sqrt(np.mean(error ** 2)))}


def predict(model, loader, device):
    model.eval()
    predictions, targets = [], []
    with torch.inference_mode():
        for x, y in loader:
            predictions.append((model(x.to(device).float()) * TARGET_SCALE).cpu().numpy())
            targets.append((y * TARGET_SCALE).numpy())
    return np.concatenate(predictions), np.concatenate(targets)


def sanity_checks(model, device):
    fens = [START_FEN, START_FEN.replace("RNBQKBNR", "RNB1KBNR"),
            START_FEN.replace("rnbqkbnr", "rnb1kbnr")]
    x = torch.from_numpy(np.stack([features_from_fen(f) for f in fens])).float().to(device)
    with torch.inference_mode():
        scores = (model(x) * TARGET_SCALE).cpu().tolist()
    return {"start_cp": scores[0], "without_white_queen_cp": scores[1],
            "without_black_queen_cp": scores[2],
            "balanced_start_abs_le_150": abs(scores[0]) <= 150,
            "white_queen_removal_shift_le_minus_300": scores[1] - scores[0] <= -300,
            "black_queen_removal_shift_ge_300": scores[2] - scores[0] >= 300}


def train(args):
    if min(args.epochs, args.batch_size, args.patience, args.threads) < 1 or not np.isfinite(args.learning_rate) or args.learning_rate <= 0:
        raise ValueError("Training counts and learning rate must be positive")
    os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    torch.set_num_threads(args.threads)
    torch.use_deterministic_algorithms(True)
    device = torch.device(("cuda" if torch.cuda.is_available() else "cpu") if args.device == "auto" else args.device)
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    with np.load(args.data, allow_pickle=False) as data:
        x, y, splits, fens = data["X"], data["y"], data["split"], data["fen"]
        metadata = json.loads(str(data["metadata"]))
    if metadata.get("feature_version") != FEATURE_VERSION or metadata.get("target_perspective") != "white":
        raise ValueError("Incompatible dataset contract")
    if x.shape != (len(y), 773) or splits.shape != y.shape or fens.shape != y.shape or not np.isfinite(y).all():
        raise ValueError("Invalid dataset dimensions/targets")
    if not np.isin(splits, [0, 1, 2]).all() or any(not np.any(splits == i) for i in range(3)):
        raise ValueError("Need nonempty train/validation/test splits")
    keys = [" ".join(f.split()[:3]) for f in fens]
    if len(set(keys)) != len(keys):
        raise ValueError("Duplicate feature positions in dataset")
    loaders = []
    for i in range(3):
        mask = splits == i
        dataset = TensorDataset(torch.from_numpy(x[mask]), torch.from_numpy(y[mask] / TARGET_SCALE))
        loaders.append(DataLoader(dataset, batch_size=args.batch_size, shuffle=i == 0,
                                  generator=torch.Generator().manual_seed(args.seed)))
    model = EvaluatorNet().to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate)
    best, stale, history = float("inf"), 0, []
    checkpoint_path = out / "best.pt"
    with open(args.data, "rb") as file:
        digest = hashlib.file_digest(file, "sha256").hexdigest()
    for epoch in range(1, args.epochs + 1):
        model.train()
        total, count = 0.0, 0
        for batch_x, batch_y in loaders[0]:
            batch_x, batch_y = batch_x.to(device).float(), batch_y.to(device)
            optimizer.zero_grad(set_to_none=True)
            loss = torch.nn.functional.mse_loss(model(batch_x), batch_y)
            if not torch.isfinite(loss):
                raise ValueError("Training diverged")
            loss.backward()
            optimizer.step()
            total += loss.item() * len(batch_y)
            count += len(batch_y)
        val_prediction, val_target = predict(model, loaders[1], device)
        validation = metrics(val_prediction, val_target)
        row = {"epoch": epoch, "train_loss": total / count, "validation": validation}
        history.append(row)
        print(json.dumps(row), flush=True)
        if validation["loss"] < best:
            best, stale = validation["loss"], 0
            torch.save({"state_dict": model.state_dict(), "epoch": epoch,
                        "feature_version": FEATURE_VERSION, "model_version": MODEL_VERSION,
                        "target_scale": TARGET_SCALE, "validation": validation,
                        "arguments": vars(args), "dataset_metadata": metadata,
                        "dataset_sha256": digest, "synthetic": args.synthetic}, checkpoint_path)
        else:
            stale += 1
            if stale >= args.patience:
                break
    model, checkpoint = load_checkpoint(checkpoint_path)
    model.to(device)
    prediction, target = predict(model, loaders[2], device)
    report = {"synthetic_smoke_only": args.synthetic, "best_epoch": checkpoint["epoch"],
              "validation": checkpoint["validation"], "test": metrics(prediction, target),
              "test_clipped": metrics(np.clip(prediction, -1500, 1500), target),
              "sanity": sanity_checks(model, device), "history": history,
              "dataset_sha256": digest, "device": str(device),
              "versions": {"torch": str(torch.__version__), "numpy": np.__version__}, "ranges": {}}
    for name, mask in [("equal_abs_lt_100", abs(target) < 100),
                       ("moderate_100_to_800", (abs(target) >= 100) & (abs(target) < 800)),
                       ("winning_abs_ge_800", abs(target) >= 800)]:
        report["ranges"][name] = metrics(prediction[mask], target[mask]) if mask.any() else {"count": 0}
    (out / "metrics.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.scatter(target, prediction, s=5, alpha=0.3)
    ax.plot([-1500, 1500], [-1500, 1500], "k--")
    ax.set(xlabel="Synthetic target (White cp)" if args.synthetic else "Stockfish target (White cp)", ylabel="Prediction (White cp)",
           title="Synthetic smoke test" if args.synthetic else "Held-out test predictions")
    fig.tight_layout()
    fig.savefig(out / "prediction_vs_target.png", dpi=150)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.hist(prediction - target, bins=50)
    ax.set(xlabel="Prediction minus target (cp)", ylabel="Positions",
           title="Synthetic smoke errors" if args.synthetic else "Held-out test errors")
    fig.tight_layout()
    fig.savefig(out / "error_distribution.png", dpi=150)
    plt.close(fig)
    print(json.dumps({k: v for k, v in report.items() if k != "history"}, indent=2))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", required=True)
    parser.add_argument("--output-dir", default="ml/models")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--batch-size", type=int, default=512)
    parser.add_argument("--learning-rate", type=float, default=0.001)
    parser.add_argument("--patience", type=int, default=10)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--synthetic", action="store_true", help="Mark smoke checkpoints, never deploy as a trained evaluator")
    train(parser.parse_args())


if __name__ == "__main__":
    main()
