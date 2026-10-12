"""Feature contract v1: PNBRQKpnbrqk planes, a1=0; turn; KQkq."""
import numpy as np

FEATURE_VERSION = 1
INPUT_SIZE = 773
PIECES = "PNBRQKpnbrqk"
START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"


def parse_fen(fen):
    if not isinstance(fen, str):
        raise ValueError("FEN must be text")
    fields = fen.split()
    if len(fields) not in (4, 6):
        raise ValueError("Expected four or six FEN fields")
    placement, turn, rights, ep = fields[:4]
    if turn not in ("w", "b"):
        raise ValueError("Invalid side to move")
    if rights != "-" and (not rights or any(c not in "KQkq" for c in rights)
                           or len(set(rights)) != len(rights)):
        raise ValueError("Invalid standard-chess castling rights")
    rights = "".join(c for c in "KQkq" if c in rights) or "-"
    if ep != "-" and (len(ep) != 2 or ep[0] not in "abcdefgh"
                       or ep[1] != ("6" if turn == "w" else "3")):
        raise ValueError("Invalid en passant square")
    if len(fields) == 6:
        if not fields[4].isdigit() or not fields[5].isdigit() or int(fields[5]) < 1:
            raise ValueError("Invalid FEN counters")
    ranks = placement.split("/")
    if len(ranks) != 8:
        raise ValueError("Expected eight ranks")
    pieces = []
    for row, rank in enumerate(ranks):
        file = 0
        previous_digit = False
        for char in rank:
            if char in "12345678":
                if previous_digit:
                    raise ValueError("Noncanonical empty-square run")
                file += int(char)
                previous_digit = True
            elif char in PIECES:
                if file >= 8 or (char in "Pp" and row in (0, 7)):
                    raise ValueError("Invalid piece square")
                pieces.append((PIECES.index(char), (7 - row) * 8 + file))
                file += 1
                previous_digit = False
            else:
                raise ValueError("Invalid piece character")
        if file != 8:
            raise ValueError("Invalid rank width")
    if sum(p == 5 for p, _ in pieces) != 1 or sum(p == 11 for p, _ in pieces) != 1:
        raise ValueError("Expected one king per side")
    return pieces, turn, rights, f"{placement} {turn} {rights} {ep}"


def features_from_fen(fen):
    pieces, turn, rights, _ = parse_fen(fen)
    features = np.zeros(INPUT_SIZE, dtype=np.int8)
    for plane, square in pieces:
        features[plane * 64 + square] = 1
    features[768] = 1 if turn == "w" else -1
    features[769:] = [int(c in rights) for c in "KQkq"]
    return features
