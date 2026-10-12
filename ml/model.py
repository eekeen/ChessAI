"""Shared architecture and checkpoint contract for training and export."""
import torch
from torch import nn
from features import FEATURE_VERSION, INPUT_SIZE

TARGET_SCALE = 1000.0
MODEL_VERSION = "chessai-mlp-v1"


class EvaluatorNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.layers = nn.Sequential(nn.Linear(INPUT_SIZE, 128), nn.ReLU(),
                                    nn.Linear(128, 64), nn.ReLU(), nn.Linear(64, 1))

    def forward(self, x):
        return self.layers(x).squeeze(-1)


def load_checkpoint(path):
    checkpoint = torch.load(path, map_location="cpu", weights_only=True)
    if (checkpoint.get("model_version") != MODEL_VERSION
            or checkpoint.get("feature_version") != FEATURE_VERSION
            or checkpoint.get("target_scale") != TARGET_SCALE):
        raise ValueError("Unsupported checkpoint contract")
    model = EvaluatorNet()
    model.load_state_dict(checkpoint["state_dict"], strict=True)
    if any(not torch.isfinite(p).all() for p in model.parameters()):
        raise ValueError("Non-finite model parameters")
    return model.eval(), checkpoint
