"""Pure diagnostic calculations. Scores are White centipawns unless stated otherwise."""
import numpy as np

MODES = ("classic", "ml", "hybrid")


def distribution(values):
    x = np.asarray(values, dtype=float)
    if not len(x):
        return {"count": 0}
    absolute = np.abs(x)
    result = {"count": len(x), "mean": float(x.mean()), "std": float(x.std()),
              "min": float(x.min()), "max": float(x.max())}
    for q in (50, 90, 95, 99):
        result[f"abs_p{q}"] = float(np.percentile(absolute, q))
        result[f"signed_p{q}"] = float(np.percentile(x, q))
    for limit in (100, 300, 500, 800):
        result[f"abs_over_{limit}_percent"] = float(100 * np.mean(absolute > limit))
    return result


def average_ranks(x):
    x = np.asarray(x)
    return np.array([np.sum(x < v) + (np.sum(x == v) - 1) / 2 for v in x], float)


def rank_metrics(prediction, target, side):
    """Stable input/UCI order breaks prediction ties; target ties all count as best."""
    sign = 1 if side == "w" else -1
    p, t = sign * np.asarray(prediction, float), sign * np.asarray(target, float)
    order = np.argsort(-p, kind="stable")
    best = t == t.max()
    top = p == p.max()
    a, b = np.triu_indices(len(t), 1)
    truth, predicted = np.sign(t[a] - t[b]), np.sign(p[a] - p[b])
    mask = truth != 0
    pairwise = np.mean((truth[mask] == predicted[mask]) + .5 * (predicted[mask] == 0)) if mask.any() else None
    rp, rt = average_ranks(p), average_ranks(t)
    correlation = float(np.corrcoef(rp, rt)[0, 1]) if rp.std() and rt.std() else None
    return {"top1": float(best[order[0]]), "top3_contains_target_best": float(best[order[:3]].any()),
            "top1_uniform_tie_expectation": float(best[top].mean()),
            "pairwise_accuracy": None if pairwise is None else float(pairwise),
            "pairwise_comparable_pairs": int(mask.sum()), "spearman": correlation,
            "regret_cp": float(t.max() - t[order[0]]),
            "regret_uniform_tie_expectation_cp": float(t.max() - t[top].mean())}


def ranking_summary(records):
    keys = ("top1", "top3_contains_target_best", "top1_uniform_tie_expectation", "pairwise_accuracy",
            "spearman", "regret_cp", "regret_uniform_tie_expectation_cp")
    out = {"parents": len(records)}
    for key in keys:
        values = [r[key] for r in records if r[key] is not None]
        out[key] = float(np.mean(values)) if values else None
        out[key + "_parents"] = len(values)
    return out


def stability(parents):
    out = {}
    for mode in (*MODES, "direct_raw", "hybrid_raw"):
        out[mode] = {}
        for group in ("all", "capture", "quiet"):
            edges = [(r["parent"][mode], c[mode]) for r in parents for c in r["children"]
                     if group == "all" or c["capture"] == (group == "capture")]
            stats = distribution([b-a for a, b in edges])
            stats["sign_flip_percent"] = float(100 * np.mean([a*b < 0 for a, b in edges])) if edges else None
            out[mode][group] = stats
    return out


def corrections(rows):
    classic = np.array([r["classic"] for r in rows], float)
    out = {}
    for kind in ("deployed_hybrid_minus_classic", "raw_residual"):
        correction = np.array([r["hybrid"]-r["classic"] if kind.startswith("deployed") else r["residual_raw"] for r in rows])
        groups = {"all": np.ones(len(rows), bool)}
        for lo, hi in ((0, 100), (100, 300), (300, 800), (800, 1500), (1500, np.inf)):
            groups[f"{lo}_to_{hi}"] = (abs(classic) >= lo) & (abs(classic) < hi)
        out[kind] = {}
        for name, mask in groups.items():
            c, d = classic[mask], correction[mask]
            stats = distribution(d)
            stats["sign_flip_percent"] = float(100*np.mean(c*(c+d) < 0)) if len(c) else None
            stats["exceeds_classic_magnitude_percent"] = float(100*np.mean(abs(d) > abs(c))) if len(c) else None
            out[kind][name] = stats
    return out


def clipping_pairs(parents, raw_key, tolerance):
    pairs, changed, affected, eligible = 0, 0, 0, 0
    for row in parents:
        raw = np.array([c[raw_key] for c in row["children"]])
        if len(raw) < 2:
            continue
        eligible += 1
        a, b = np.triu_indices(len(raw), 1)
        clipped = np.clip(raw, -1500, 1500)
        lost = (abs(raw[a]-raw[b]) > tolerance) & (abs(clipped[a]-clipped[b]) <= tolerance)
        pairs += len(a)
        changed += int(lost.sum())
        affected += int(lost.any())
    return {"tolerance_cp": tolerance, "pairs": pairs, "new_tied_pairs": changed,
            "pair_percent": 100*changed/pairs if pairs else None,
            "parents": eligible, "affected_parents": affected,
            "affected_parent_percent": 100*affected/eligible if eligible else None}
