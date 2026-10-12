"""Load a frozen independently authored opening manifest, checking legal histories."""
import csv
import hashlib
import json
from pathlib import Path
import chess

ROOT = Path(__file__).resolve().parent


def normalized(board):
    # Legal EP normalization also catches positions differing only by an irrelevant EP target.
    return ' '.join(board.fen(en_passant='legal').split()[:4])


def load_openings(path=ROOT/'openings-v1.tsv', check_freeze=True):
    path = Path(path)
    if check_freeze:
        frozen = json.loads((ROOT/'openings-v1.freeze.json').read_text())
        if hashlib.sha256(path.read_bytes()).hexdigest() != frozen['sha256']:
            raise ValueError('Frozen external opening manifest hash mismatch')
    with path.open(encoding='utf-8', newline='') as stream: rows = list(csv.DictReader(stream, delimiter='\t'))
    seen, ids = set(), set()
    for row in rows:
        if row['id'] in ids: raise ValueError('Duplicate opening ID')
        ids.add(row['id'])
        board = chess.Board()
        moves = row['moves'].split()
        if not 8 <= len(moves) <= 12: raise ValueError('Opening outside 8-12 plies')
        for move in moves: board.push_uci(move)
        if not board.is_valid() or board.is_game_over(): raise ValueError('Invalid/terminal opening')
        if board.fen(en_passant='fen') != row['fen']: raise ValueError('Opening FEN/history mismatch')
        key = normalized(board)
        if key in seen: raise ValueError('Duplicate normalized opening FEN')
        seen.add(key)
    if check_freeze and len(rows) != 64: raise ValueError('Final external suite must contain 64 positions')
    return rows


def ordered(rows, seed):
    return sorted(rows, key=lambda row: hashlib.sha256(f'{seed}:{row["id"]}'.encode()).digest())


def schedule(rows, levels, seed):
    result = []
    level_order = sorted(levels, key=lambda level: hashlib.sha256(f'{seed}:elo:{level}'.encode()).digest())
    for index, opening in enumerate(ordered(rows, seed)):
        for offset in range(len(level_order)):
            level = level_order[(index+offset) % len(level_order)]
            for color in ('white', 'black'):
                result.append({'number': len(result)+1, 'opening_id': opening['id'],
                               'opponent_elo': level, 'chessai_color': color})
    return result
