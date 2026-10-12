"""Validation-only material perturbations. No fabricated Stockfish labels."""
from features import START_FEN


def cases():
    result = []
    for side in ("w", "b"):
        anchor = START_FEN.replace(" w ", f" {side} ")
        for color, rank, sign in [("white", "RNBQKBNR", -1), ("black", "rnbqkbnr", 1)]:
            for piece, index, minimum in [("queen", 3, 300), ("rook", 0, 150),
                                          ("knight", 1, 80), ("bishop", 2, 80)]:
                missing = rank[:index] + "1" + rank[index + 1:]
                fen = anchor.replace(rank, missing)
                if piece == "rook":
                    fields = fen.split()
                    fields[2] = fields[2].replace("Q" if color == "white" else "q", "") or "-"
                    fen = " ".join(fields)
                result.append(dict(name=f"{side}_to_move_without_{color}_{piece}",
                                   fen=fen, anchor=anchor,
                                   direction=sign, minimum_shift_cp=minimum))
    # Legal simplified positions, compared to the same board with bare kings.
    anchor = "4k3/8/8/8/8/8/8/4K3 w - - 0 1"
    for piece, minimum in [("Q", 300), ("R", 150), ("B", 0), ("N", 0)]:
        # A lone bishop/knight cannot force mate; only report, no material shift gate.
        for white in (True, False):
            fen = anchor.replace("4K3", piece + "3K3") if white else anchor.replace("4k3", piece.lower() + "3k3")
            result.append(dict(name=f"simplified_{'white' if white else 'black'}_{piece}", fen=fen,
                               anchor=anchor, direction=1 if white else -1, minimum_shift_cp=minimum))
    return result


def evaluate(models, device, tool):
    """Evaluate the whole suite; never supply these positions to the trainer."""
    import numpy as np
    import torch
    from features_v2 import features_from_fen
    from prepare_v2 import classic_scores
    suite = cases()
    fens = [START_FEN] + [fen for item in suite for fen in (item["anchor"], item["fen"])]
    x = np.stack([features_from_fen(fen) for fen in fens])
    classic = classic_scores(tool, fens)
    report = {}
    for name in ["classic", *models]:
        if name == "classic":
            scores = classic.copy()
        else:
            model = models[name].eval()
            batch = torch.from_numpy(x[:, :773] if name == "v1_direct" else x).to(device)
            with torch.inference_mode():
                scores = (model(batch) * 1000).cpu().numpy()
        if name == "residual":
            scores += classic
        entries = []
        for i, item in enumerate(suite):
            anchor_cp, cp = float(scores[1 + 2 * i]), float(scores[2 + 2 * i])
            shift = cp - anchor_cp
            entries.append(dict(**item, anchor_cp=anchor_cp, prediction_cp=cp, shift_cp=shift,
                                passed=shift * item["direction"] >= item["minimum_shift_cp"] if item["minimum_shift_cp"] else None))
        report[name] = dict(start_cp=float(scores[0]), balanced_start=abs(float(scores[0])) <= 150, cases=entries)
    return report
