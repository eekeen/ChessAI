"""One-time authored suite construction. Refuses to replace an already frozen suite.
No engine evaluation or match results are read. SAN continuations are authored here.
"""
import csv
import hashlib
import json
from pathlib import Path
import chess

ROOT = Path(__file__).resolve().parent
# Each independent base has two quiet/common continuations: 32 x 2 = 64 positions.
LINES = [
 ('Italian', 'e4 e5 Nf3 Nc6 Bc4 Bc5 d3 Nf6', 'O-O d6', 'Nc3 d6'),
 ('Ruy Lopez', 'e4 e5 Nf3 Nc6 Bb5 a6 Ba4 Nf6', 'd3 b5', 'Nc3 b5'),
 ('Scotch', 'e4 e5 Nf3 Nc6 d4 exd4 Nxd4 Bc5', 'Nb3 Bb6', 'Be3 Bb6'),
 ('Four Knights', 'e4 e5 Nf3 Nc6 Nc3 Nf6 Bb5 Bb4', 'O-O O-O', 'd3 d6'),
 ('Petrov', 'e4 e5 Nf3 Nf6 Nxe5 d6 Nf3 Nxe4', 'Nc3 Nxc3 bxc3 Be7', 'd3 Nf6'),
 ('Vienna', 'e4 e5 Nc3 Nc6 Bc4 Nf6 d3 Bc5', 'Nge2 d6', 'Be3 Bb6'),
 ('Sicilian Najdorf', 'e4 c5 Nf3 d6 d4 cxd4 Nxd4 Nf6 Nc3 a6', 'Be3 e6', 'g3 e5'),
 ('Sicilian Dragon', 'e4 c5 Nf3 d6 d4 cxd4 Nxd4 Nf6 Nc3 g6', 'g3 Bg7', 'Be2 Bg7'),
 ('Sicilian Taimanov', 'e4 c5 Nf3 e6 d4 cxd4 Nxd4 Nc6', 'Nc3 a6', 'Nxc6 bxc6'),
 ('Sicilian Kan', 'e4 c5 Nf3 e6 d4 cxd4 Nxd4 a6', 'c4 Nf6', 'Nc3 b5'),
 ('Sicilian Closed', 'e4 c5 Nc3 Nc6 g3 g6 Bg2 Bg7', 'd3 d6', 'Nge2 d6'),
 ('French Advance', 'e4 e6 d4 d5 e5 c5 c3 Nc6', 'Nf3 Qb6', 'Be3 Qb6'),
 ('French Exchange', 'e4 e6 d4 d5 exd5 exd5 Nf3 Nf6', 'Bd3 Bd6', 'Be2 Bd6'),
 ('French Tarrasch', 'e4 e6 d4 d5 Nd2 Nf6 e5 Nfd7', 'Bd3 c5', 'Ngf3 c5'),
 ('Caro-Kann Advance', 'e4 c6 d4 d5 e5 Bf5 Nf3 e6', 'Bd3 Bxd3 Qxd3 Nd7', 'c3 Nd7'),
 ('Caro-Kann Panov', 'e4 c6 d4 d5 exd5 cxd5 c4 Nf6', 'Nc3 e6', 'Nf3 e6'),
 ('Scandinavian Qa5', 'e4 d5 exd5 Qxd5 Nc3 Qa5 d4 Nf6', 'Nf3 c6', 'Bc4 c6'),
 ('Scandinavian Qd6', 'e4 d5 exd5 Qxd5 Nc3 Qd6 d4 Nf6', 'Nf3 a6', 'g3 a6'),
 ('Queens Gambit Declined', 'd4 d5 c4 e6 Nc3 Nf6 Nf3 Be7', 'Bg5 h6', 'e3 O-O'),
 ('Queens Gambit Accepted', 'd4 d5 c4 dxc4 Nf3 Nf6 e3 e6', 'Bxc4 c5', 'Bxc4 a6'),
 ('Slav Exchange', 'd4 d5 c4 c6 cxd5 cxd5 Nc3 Nf6', 'Bf4 Nc6', 'Nf3 Nc6'),
 ('Semi-Slav', 'd4 d5 c4 c6 Nf3 Nf6 Nc3 e6', 'e3 a6', 'Qc2 Nbd7'),
 ('Kings Indian', 'd4 Nf6 c4 g6 Nc3 Bg7 e4 d6', 'Be2 O-O', 'g3 O-O'),
 ('Queens Indian', 'd4 Nf6 c4 e6 Nf3 b6 g3 Bb7', 'Bg2 Be7', 'Nc3 Bb4'),
 ('Nimzo Rubinstein', 'd4 Nf6 c4 e6 Nc3 Bb4 e3 O-O', 'Bd3 d5', 'Nf3 d5'),
 ('Nimzo Classical', 'd4 Nf6 c4 e6 Nc3 Bb4 Qc2 O-O', 'a3 Bxc3+ Qxc3 d5', 'Nf3 d5'),
 ('English Symmetrical', 'c4 c5 Nc3 Nc6 g3 g6 Bg2 Bg7', 'Nf3 Nf6', 'e3 e6'),
 ('English Reversed Sicilian', 'c4 e5 Nc3 Nf6 g3 d5 cxd5 Nxd5', 'Bg2 Nb6', 'Nf3 Nc6'),
 ('Reti', 'Nf3 d5 g3 Nf6 Bg2 g6 O-O Bg7', 'd3 O-O', 'b3 O-O'),
 ('Catalan', 'd4 Nf6 c4 e6 Nf3 d5 g3 Be7', 'Bg2 O-O', 'Nc3 O-O'),
 ('Pirc', 'e4 d6 d4 Nf6 Nc3 g6 Nf3 Bg7', 'Be2 O-O', 'h3 O-O'),
 ('Dutch', 'd4 f5 g3 Nf6 Bg2 e6 Nf3 Be7', 'O-O O-O', 'c4 O-O'),
]


def main():
    destination = ROOT/'openings-v1.tsv'
    if destination.exists() or (ROOT/'openings-v1.freeze.json').exists():
        raise SystemExit('Suite v1 is already frozen; never regenerate it from match results')
    rows, seen = [], set()
    for family, base, *tails in LINES:
        for variant, tail in enumerate(tails, 1):
            board, moves = chess.Board(), []
            for san in (base+' '+tail).split():
                move = board.parse_san(san)
                moves.append(move.uci()); board.push(move)
            assert board.is_valid() and not board.is_game_over(), family
            assert 8 <= len(moves) <= 12
            key = ' '.join(board.fen(en_passant='legal').split()[:4])
            assert key not in seen, (family, variant)
            seen.add(key)
            rows.append({'id': f'ext-{len(rows)+1:02d}', 'family': family, 'variant': variant,
                         'fen': board.fen(en_passant='fen'), 'moves': ' '.join(moves)})
    assert len(rows) == 64
    internal = set()
    for path in (ROOT.parent/'suites').glob('*.tsv'):
        for line in path.read_text().splitlines()[1:]:
            fen = line.split('\t')[2]
            internal.add(' '.join(chess.Board(fen+' 0 1').fen(en_passant='legal').split()[:4]))
    overlap = [r['id']+': '+r['family'] for r in rows if ' '.join(chess.Board(r['fen']).fen(en_passant='legal').split()[:4]) in internal]
    assert not overlap, overlap
    with destination.open('x', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=['id','family','variant','fen','moves'], delimiter='\t', lineterminator='\n')
        writer.writeheader(); writer.writerows(rows)
    digest = hashlib.sha256(destination.read_bytes()).hexdigest()
    (ROOT/'openings-v1.freeze.json').write_text(json.dumps({'version': 'external-calibration-openings-v1',
        'positions': 64, 'sha256': digest, 'selection': 'authored common opening lines; no engine scores or outcomes consulted',
        'policy': 'immutable after creation; never modify based on match results'}, indent=2)+'\n')
    print(digest)


if __name__ == '__main__': main()
