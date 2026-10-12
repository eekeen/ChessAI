"""Test fixture only: deliberately NOT a calibrated chess opponent."""
import argparse
import os
import sys
import time
import chess

p = argparse.ArgumentParser()
p.add_argument('--mode', default='normal')
p.add_argument('--min-elo', type=int, default=1200)
p.add_argument('--max-elo', type=int, default=2600)
p.add_argument('--log')
args = p.parse_args()
board = chess.Board()
for raw in sys.stdin:
    line = raw.strip()
    if args.log:
        with open(args.log, 'a') as stream: stream.write(line+'\n')
    if line == 'uci':
        if args.mode == 'startup-crash': os._exit(3)
        if args.mode == 'startup-timeout': time.sleep(120)
        print('id name Stockfish FAKE TEST FIXTURE')
        print('option name Threads type spin default 1 min 1 max 16')
        print('option name Hash type spin default 16 min 1 max 128')
        print('option name UCI_LimitStrength type check default false')
        if args.mode != 'missing-elo': print(f'option name UCI_Elo type spin default {args.min_elo} min {args.min_elo} max {args.max_elo}')
        print('option name Skill Level type spin default 20 min 0 max 20')
        print('option name Ponder type check default false')
        print('option name MultiPV type spin default 1 min 1 max 256')
        print('option name Clear Hash type button')
        print('uciok', flush=True)
    elif line == 'isready': print('readyok', flush=True)
    elif line.startswith('position '):
        if line.startswith('position startpos'):
            _, _, moves = line.partition(' moves ')
            board = chess.Board()
        else:
            fen, _, moves = line[13:].partition(' moves ')
            board = chess.Board(fen)
        for move in moves.split(): board.push_uci(move)
    elif line.startswith('go '):
        if args.mode == 'crash': os._exit(4)
        if args.mode == 'timeout': time.sleep(120)
        move = 'a1a8' if args.mode == 'illegal' else sorted(move.uci() for move in board.legal_moves)[0]
        print('info depth 1 nodes 17 time 1')
        print('bestmove '+move, flush=True)
    elif line == 'quit': break
