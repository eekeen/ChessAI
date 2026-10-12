"""Train matched direct/residual experiments on unchanged V1 dataset splits."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import numpy as np
import torch
from torch.utils.data import DataLoader, TensorDataset
from features_v2 import INPUT_SIZE, SCHEMA_HASH
from model_v2 import EvaluatorNetV2, TARGET_SCALE, load_checkpoint
from prepare_v2 import classic_scores
from material_sanity import evaluate as evaluate_sanity


def metrics(prediction, target):
    error = np.asarray(prediction, dtype=np.float64) - target
    return dict(count=len(error), mae_cp=float(np.abs(error).mean()), rmse_cp=float(np.sqrt((error ** 2).mean())))


def predict(model, x, device, batch_size=2048):
    model.eval()
    result = []
    with torch.inference_mode():
        for start in range(0, len(x), batch_size):
            batch = torch.from_numpy(x[start:start + batch_size]).to(device).float()
            result.append((model(batch) * TARGET_SCALE).cpu().numpy())
    return np.concatenate(result)


def loss_value(error, kind, delta):
    error = np.asarray(error, dtype=np.float64) / TARGET_SCALE
    if kind == "mse":
        return float(np.mean(error ** 2))
    absolute = np.abs(error)
    return float(np.mean(np.where(absolute <= delta, 0.5 * error ** 2, delta * (absolute - 0.5 * delta))))


def train_one(kind, args, x, y, classic, splits, metadata, digest, device):
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    model = EvaluatorNetV2(args.dropout).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=args.weight_decay)
    target = (y - classic if kind == "residual" else y) / TARGET_SCALE
    train_mask, val_mask = splits == 0, splits == 1
    loader = DataLoader(TensorDataset(torch.from_numpy(x[train_mask]), torch.from_numpy(target[train_mask])),
                        batch_size=args.batch_size, shuffle=True, generator=torch.Generator().manual_seed(args.seed))
    val_x = x[val_mask]
    best, stale, history = float("inf"), 0, []
    output = Path(args.output_dir)
    path = output / f"{kind}_best.pt"
    criterion = torch.nn.MSELoss() if args.loss == "mse" else torch.nn.HuberLoss(delta=args.huber_delta)
    for epoch in range(1, args.epochs + 1):
        model.train()
        total, count = 0.0, 0
        for batch_x, batch_y in loader:
            batch_x, batch_y = batch_x.to(device), batch_y.to(device)
            optimizer.zero_grad(set_to_none=True)
            loss = criterion(model(batch_x), batch_y)
            if not torch.isfinite(loss):
                raise ValueError("Nonfinite training loss")
            loss.backward()
            optimizer.step()
            total += loss.item() * len(batch_y)
            count += len(batch_y)
        val_pred = predict(model, val_x, device)
        if kind == "residual":
            val_pred += classic[val_mask]
        validation = metrics(val_pred, y[val_mask])
        value = loss_value(val_pred - y[val_mask], args.loss, args.huber_delta)
        row = dict(kind=kind, epoch=epoch, train_loss=total / count, validation_loss=value, validation=validation)
        print(json.dumps(row), flush=True)
        history.append(row)
        (output / f"{kind}_history.json").write_text(json.dumps(history, indent=2))
        if value < best:
            best, stale = value, 0
            temporary = path.with_suffix(".tmp")
            torch.save(dict(state_dict=model.state_dict(), feature_version=2, schema_sha256=SCHEMA_HASH,
                            target_scale=TARGET_SCALE, kind=kind, dropout=args.dropout,
                            epoch=epoch, validation=validation, validation_loss=value,
                            dataset_sha256=digest, dataset_metadata=metadata, arguments=vars(args),
                            synthetic=args.synthetic), temporary)
            os.replace(temporary, path)
        else:
            stale += 1
            if stale >= args.patience:
                break
    model, checkpoint = load_checkpoint(path)
    return model.to(device), checkpoint, history


def range_metrics(prediction, target):
    return {name: metrics(prediction[mask], target[mask]) if mask.any() else {"count": 0}
            for name, mask in [("abs_lt_100", abs(target) < 100),
                               ("abs_100_to_800", (abs(target) >= 100) & (abs(target) < 800)),
                               ("abs_ge_800", abs(target) >= 800)]}


def train(args):
    if min(args.epochs, args.batch_size, args.patience, args.threads) <= 0:
        raise ValueError("Counts must be positive")
    if not 0 <= args.dropout < 1 or args.weight_decay < 0 or args.learning_rate <= 0 or args.huber_delta <= 0:
        raise ValueError("Invalid optimizer/loss settings")
    os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    torch.set_num_threads(args.threads)
    torch.use_deterministic_algorithms(True)
    device = torch.device(("cuda" if torch.cuda.is_available() else "cpu") if args.device == "auto" else args.device)
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    if any((output / f"{kind}_best.pt").exists() for kind in ("direct", "residual")):
        raise ValueError("Use a fresh output directory to preserve prior experiments")
    with np.load(args.data, allow_pickle=False) as data:
        x, y, classic, residual, splits, fens = (data[k] for k in ("X", "y", "classic", "residual", "split", "fen"))
        metadata = json.loads(str(data["metadata"]))
    if metadata.get("feature_version") != 2 or metadata.get("schema_sha256") != SCHEMA_HASH:
        raise ValueError("Incompatible V2 features")
    if x.shape != (len(y), INPUT_SIZE) or any(a.shape != y.shape for a in (classic, residual, splits, fens)):
        raise ValueError("Invalid dataset dimensions")
    if not np.isfinite(x).all() or not np.isfinite(y).all() or not np.isfinite(classic).all():
        raise ValueError("Nonfinite dataset")
    np.testing.assert_array_equal(residual, y - classic)
    if not np.isin(splits, [0, 1, 2]).all() or any(not (splits == i).any() for i in range(3)):
        raise ValueError("Invalid splits")
    if len(set(" ".join(f.split()[:3]) for f in fens)) != len(fens):
        raise ValueError("Duplicate feature positions")
    # Validate provenance against the current C++ helper before learning corrections.
    probe = np.linspace(0, len(y) - 1, min(128, len(y)), dtype=int)
    np.testing.assert_array_equal(classic_scores(args.tool, fens[probe]), classic[probe])
    with open(args.data, "rb") as file:
        digest = hashlib.file_digest(file, "sha256").hexdigest()
    trained = {kind: train_one(kind, args, x, y, classic, splits, metadata, digest, device)
               for kind in ("direct", "residual")}
    models = {kind: value[0] for kind, value in trained.items()}
    if args.baseline:
        from model import load_checkpoint as load_v1
        baseline, baseline_checkpoint = load_v1(args.baseline)
        if baseline_checkpoint.get("dataset_sha256") != metadata["source_dataset_sha256"]:
            raise ValueError("V1 checkpoint was trained on a different dataset")
        models["v1_direct"] = baseline.to(device)
    report = dict(arguments=vars(args), device=str(device), dataset_sha256=digest, schema_sha256=SCHEMA_HASH,
                  synthetic=args.synthetic, versions=dict(torch=str(torch.__version__), numpy=np.__version__),
                  best_epochs={kind: item[1]["epoch"] for kind, item in trained.items()}, metrics={})
    test_predictions = {}
    for name in ["classic", *models]:
        report["metrics"][name] = {}
        for split_name, split_id in [("validation", 1), ("test", 2)]:
            mask = splits == split_id
            prediction = classic[mask].copy() if name == "classic" else predict(
                models[name], x[mask, :773] if name == "v1_direct" else x[mask], device)
            if name == "residual":
                prediction += classic[mask]
            report["metrics"][name][split_name] = dict(raw=metrics(prediction, y[mask]),
                clipped=metrics(np.clip(prediction, -1500, 1500), y[mask]),
                ranges=range_metrics(prediction, y[mask]))
            if split_id == 2:
                test_predictions[name] = prediction
    report["material_sanity"] = evaluate_sanity(models, device, args.tool)
    (output / "comparison.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 2, figsize=(10, 8))
    target = y[splits == 2]
    for col, name in enumerate(("direct", "residual")):
        prediction = test_predictions[name]
        axes[0, col].scatter(target, prediction, s=2, alpha=0.15)
        axes[0, col].plot([-1500, 1500], [-1500, 1500], "k--")
        axes[0, col].set(title=name, xlabel="Target (White cp)", ylabel="Predicted position score (cp)")
        axes[1, col].hist(prediction - target, bins=60)
        axes[1, col].set(xlabel="Prediction minus target (cp)", ylabel="Positions")
    fig.tight_layout()
    fig.savefig(output / "comparison.png", dpi=150)
    plt.close(fig)
    print(json.dumps({"best_epochs": report["best_epochs"], "metrics": report["metrics"]}, indent=2))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", default="ml/data/lichess_250k_v2.npz")
    parser.add_argument("--tool", default="build/Release/eval_tool.exe")
    parser.add_argument("--baseline", help="Preserved V1 checkpoint for matched comparison")
    parser.add_argument("--output-dir", default="ml/models/v2_huber")
    parser.add_argument("--epochs", type=int, default=60)
    parser.add_argument("--patience", type=int, default=8)
    parser.add_argument("--batch-size", type=int, default=512)
    parser.add_argument("--learning-rate", type=float, default=0.001)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--dropout", type=float, default=0.10)
    parser.add_argument("--loss", choices=["mse", "huber"], default="huber")
    parser.add_argument("--huber-delta", type=float, default=0.3, help="Normalized target units: 0.3 = 300 cp")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--synthetic", action="store_true")
    train(parser.parse_args())
