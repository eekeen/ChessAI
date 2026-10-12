"""V2 contract. JSON is the source of scalar order, constants and operations."""
import hashlib
import json
from pathlib import Path
import numpy as np
from features import features_from_fen as features_v1

SCHEMA_PATH = Path(__file__).with_name("feature_schema_v2.json")
SCHEMA = json.loads(SCHEMA_PATH.read_text())
SCHEMA_HASH = hashlib.sha256(SCHEMA_PATH.read_bytes()).hexdigest()
INPUT_SIZE = SCHEMA["base_size"] + len(SCHEMA["scalars"])


def extend_features(base):
    base = np.asarray(base, dtype=np.float32)
    if base.shape[-1] != SCHEMA["base_size"]:
        raise ValueError("Expected V1 features")
    shape = base.shape[:-1]
    counts = base[..., :768].reshape(*shape, 12, 64).sum(axis=-1)
    values = []
    for feature in SCHEMA["scalars"]:
        kind = feature["kind"]
        if kind == "count":
            value = counts[..., feature["plane"]] / feature["scale"]
        elif kind == "balance":
            value = ((counts[..., :6] - counts[..., 6:]) * SCHEMA["material_values"]).sum(axis=-1) / feature["scale"]
        elif kind == "phase":
            value = np.minimum(1, ((counts[..., :6] + counts[..., 6:]) * SCHEMA["phase_weights"]).sum(axis=-1) / feature["scale"])
        elif kind == "pair":
            value = counts[..., feature["plane"]] >= feature["threshold"]
        elif kind == "king":
            value = base[..., [feature["plane"] * 64 + s for s in feature["squares"]]].sum(axis=-1) > 0
        else:
            raise ValueError(kind)
        values.append(value)
    return np.concatenate([base, np.stack(values, axis=-1)], axis=-1).astype(np.float32)


def features_from_fen(fen):
    return extend_features(features_v1(fen))
