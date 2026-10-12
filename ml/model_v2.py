"""V2 models; V1 model.py and checkpoints remain unchanged."""
import torch
from torch import nn
from features_v2 import INPUT_SIZE, SCHEMA_HASH

TARGET_SCALE = 1000.0


class EvaluatorNetV2(nn.Module):
    def __init__(self, dropout=0.1):
        super().__init__()
        self.layers = nn.Sequential(nn.Linear(INPUT_SIZE, 128), nn.ReLU(), nn.Dropout(dropout),
                                    nn.Linear(128, 64), nn.ReLU(), nn.Linear(64, 1))

    def forward(self, x):
        return self.layers(x).squeeze(-1)


def load_checkpoint(path):
    checkpoint = torch.load(path, map_location="cpu", weights_only=True)
    if (checkpoint.get("feature_version") != 2 or checkpoint.get("schema_sha256") != SCHEMA_HASH
            or checkpoint.get("target_scale") != TARGET_SCALE or checkpoint.get("kind") not in ("direct", "residual")):
        raise ValueError("Unsupported V2 checkpoint contract")
    model = EvaluatorNetV2(checkpoint["dropout"])
    model.load_state_dict(checkpoint["state_dict"], strict=True)
    if any(not torch.isfinite(p).all() for p in model.parameters()):
        raise ValueError("Non-finite model weights")
    return model.eval(), checkpoint
