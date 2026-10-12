"""External Stockfish calibration. Never tunes ChessAI or runs final games implicitly."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import chess
from benchmarks.elo.calibration_stats import crossing, summary
from benchmarks.elo.openings import ROOT, load_openings, ordered
from benchmarks.elo.protocol import build_protocol, digest, freeze, ladder, machine, read_frozen, validate
from benchmarks.elo.transport import ChessAI, Stockfish, EngineFault, sha256


def atomic(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name+'.', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as stream: stream.write(content)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)


def termination(board):
    if board.is_checkmate(): return ('0-1' if board.turn == chess.WHITE else '1-0'), 'checkmate'
    if board.is_stalemate(): return '1/2-1/2', 'stalemate'
    if board.is_insufficient_material(): return '1/2-1/2', 'insufficient_material'
    if board.is_repetition(3): return '1/2-1/2', 'repetition'
    if board.is_fifty_moves(): return '1/2-1/2', 'fifty_move_rule'
    return None


def play(record, opening, native, opponent, config):
    board = chess.Board()
    for move in opening['moves'].split(): board.push_uci(move)
    record.update(opening_fen=opening['fen'], opening_family=opening['family'],
                  forced_moves=opening['moves'].split(), moves=[], move_timings=[], result='*',
                  termination='ongoing', plies=len(board.move_stack), searched_plies=0,
                  white='chessai' if record['chessai_color'] == 'white' else 'stockfish',
                  black='stockfish' if record['chessai_color'] == 'white' else 'chessai')
    start = time.monotonic()
    actor = 'chessai'
    try:
        native.newgame()
        actor = 'stockfish'; opponent.newgame(record['opponent_elo'])
        record['stockfish_options_used'] = dict(opponent.used)
        while True:
            end = termination(board)
            if end:
                record['result'], record['termination'] = end
                break
            if len(board.move_stack) >= config['max_plies']:
                record.update(result='1/2-1/2', termination='max_ply_draw'); break
            color = 'white' if board.turn == chess.WHITE else 'black'
            actor = record[color]
            engine = native if actor == 'chessai' else opponent
            timing = engine.move(board, config['move_time_ms'], config['response_grace_ms'])
            timing.update(engine=actor, color=color, ply=len(board.move_stack)+1,
                          requested_ms=config['move_time_ms'])
            timing['search_overrun_ms'] = (max(0, timing['search_ms']-config['move_time_ms'])
                                           if timing.get('search_ms') is not None else None)
            record['move_timings'].append(timing)
            try: move = chess.Move.from_uci(timing['move'])
            except (ValueError, KeyError) as exc: raise EngineFault('illegal_move', 'Malformed engine move') from exc
            if move not in board.legal_moves: raise EngineFault('illegal_move', f'{actor} returned {move.uci()}')
            board.push(move)
            record['moves'].append(move.uci())
            record['plies'] = len(board.move_stack)
            record['searched_plies'] = len(record['moves'])
    except EngineFault as exc:
        record.update(termination=exc.reason, fault_engine=actor, error=str(exc), invalid=True)
        # Record the forfeit for audit, but invalidate the ENTIRE run for inference.
        loser_color = 'white' if record['white'] == actor else 'black'
        record['result'] = '0-1' if loser_color == 'white' else '1-0'
    except KeyboardInterrupt:
        record.update(termination='interrupted', invalid=True)
        raise
    finally:
        record['elapsed_ms'] = 1000*(time.monotonic()-start)
        record['final_fen'] = board.fen(en_passant='fen')
    return record


def markdown(report):
    protocol = report['protocol']['protocol']
    lines = ['# External Stockfish calibration', '', f"Phase: **{protocol['purpose']}**. Complete: {report['complete']}. Valid: {report['valid']}.",
             f"Stockfish UCI_Elo calibrated under this exact **{protocol['move_time_ms']} ms/move** protocol. "
             'This is not a FIDE, Chess.com, Lichess or universal engine rating.', '',
             f"Stockfish: {protocol['stockfish']['name']}; supported UCI_Elo {protocol['stockfish']['elo_range']}.",
             f"Model `{protocol['model']}`, alpha {protocol['alpha']}. Threads 1; Hash {protocol['stockfish']['options_used']['Hash']} MiB.",
             f"Protocol SHA-256: `{report['protocol']['protocol_sha256']}`.",
             f"Opening manifest SHA-256: `{protocol['manifest_sha256']}`.", '',
             '| SF UCI_Elo | Games | W/D/L | Score | Opening-cluster 95% CI | White score | Black score | Avg plies |',
             '|---:|---:|---|---:|---|---:|---:|---:|']
    for elo, entry in report['summary']['levels'].items():
        ci = entry['score_ci95_percent']
        fmt = lambda v: 'n/a' if v is None else f'{v:.2f}%'
        lines.append(f"| {elo} | {entry['games']} | {entry['wins']}/{entry['draws']}/{entry['losses']} | {entry['score_percent']:.2f}% | "
                     + ('n/a' if ci is None else f'{ci[0]:.2f}–{ci[1]:.2f}%')
                     + f" | {fmt(entry['by_color']['white']['score_percent'])} | {fmt(entry['by_color']['black']['score_percent'])} | {entry['average_plies']:.1f} |")
    lines += ['', 'Termination counts by opponent level:', '']
    for elo, entry in report['summary']['levels'].items(): lines.append(f"- {elo}: {entry['termination_counts']}")
    lines += ['', 'Actual move timings (harness response includes IPC; search timing excludes it when reported):', '']
    for engine, timing in report.get('timing_summary', {}).items(): lines.append(f'- {engine}: `{json.dumps(timing)}`')
    estimate = report['summary']['calibration']
    if protocol['purpose'] == 'test_fixture':
        lines.insert(2, '**FAKE UCI OPPONENT — integration test only. No external playing strength was measured.**\n')
    lines += ['', f'Calibration: `{json.dumps(estimate)}`.', '',
              'Development/bracketing and smoke results are not final estimates. Bootstrap resamples complete opening pairs jointly across levels. '
              'Sparse/extreme results can give degenerate score intervals; uncertainty is conditional on this fixed suite and engine version. '
              'A missing or unstable 50% bracket produces no calibrated estimate. '
              'Stockfish strength-limited play and timed search can vary even with fixed opening order; the seed does not control Stockfish internal randomness.', '']
    return '\n'.join(lines)


def execute(payload, path, native, opponent):
    path = Path(path)
    if path.exists() or path.with_suffix('.md').exists(): raise ValueError('Result path exists; never overwrite/restart an affected run')
    config = payload['protocol']
    report = {'protocol': payload, 'machine': machine(), 'started_utc': datetime.now(timezone.utc).isoformat(),
              'complete': False, 'valid': False, 'games': [], 'summary': {}}
    openings = {row['id']: row for row in config['openings']}
    def save(infer=False):
        report['summary'] = summary(report['games'], config['seed'], config['bootstrap_iterations'], infer=infer)
        report['summary']['calibration']['phase'] = config['purpose']
        report['timing_summary'] = {}
        for engine in ('chessai','stockfish'):
            timings = [t for g in report['games'] for t in g.get('move_timings', []) if t['engine'] == engine]
            searches = [t['search_ms'] for t in timings if t.get('search_ms') is not None]
            report['timing_summary'][engine] = {'moves':len(timings),
                'mean_response_ms':sum(t['response_ms'] for t in timings)/len(timings) if timings else None,
                'mean_search_ms':sum(searches)/len(searches) if searches else None,
                'max_search_ms':max(searches) if searches else None,
                'searches_over_budget':sum(t > config['move_time_ms'] for t in searches)}
        atomic(path, json.dumps(report, indent=2, allow_nan=False)+'\n')
        atomic(path.with_suffix('.md'), markdown(report))
    save()
    try:
        for assignment in config['plan']:
            record = dict(assignment)
            report['games'].append(record)
            play(record, openings[record['opening_id']], native, opponent, config)
            print(f"Game {record['number']}/{config['games']}: SF {record['opponent_elo']}, ChessAI {record['chessai_color']}, "
                  f"{record['result']} ({record['termination']}, {record['plies']} plies)", flush=True)
            save()
            if record.get('invalid'): raise EngineFault(record['termination'], 'Engine fault invalidates the entire run; no selective replay')
        report.update(complete=True, valid=True, finished_utc=datetime.now(timezone.utc).isoformat())
        save(infer=True)
    except BaseException as exc:
        report.update(valid=False, failure=str(exc) or type(exc).__name__, finished_utc=datetime.now(timezone.utc).isoformat())
        save()
        raise
    return report


def find_stockfish(argument):
    candidate = argument or os.environ.get('STOCKFISH') or shutil.which('stockfish')
    if not candidate or not Path(candidate).is_file():
        raise ValueError('Stockfish executable not found. Supply --stockfish PATH or set STOCKFISH; no automatic download or Elo-range assumption.')
    return str(Path(candidate).resolve())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['detect', 'smoke', 'development', 'freeze', 'final'])
    parser.add_argument('--stockfish')
    parser.add_argument('--chessai', type=Path, default=Path('build/Release/ChessAI_calibration.exe'))
    parser.add_argument('--manifest', type=Path, default=ROOT/'openings-v1.tsv')
    parser.add_argument('--hash-mb', type=int, default=64)
    parser.add_argument('--time-ms', type=int, default=250)
    parser.add_argument('--max-plies', type=int, default=300)
    parser.add_argument('--grace-ms', type=int, default=2000)
    parser.add_argument('--seed', type=int, default=20260926)
    parser.add_argument('--subset', type=int, default=8, help='development pairs per level; smoke always one pair')
    parser.add_argument('--elo-step', type=int, default=200)
    parser.add_argument('--elos', help='comma-separated settings; smoke defaults to advertised minimum')
    parser.add_argument('--bootstrap', type=int, default=5000)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--protocol', type=Path)
    parser.add_argument('--protocol-sha256', help='reviewed final protocol content digest printed by freeze')
    parser.add_argument('--development', type=Path, help='completed bracketing results, required for final freeze')
    args = parser.parse_args()
    opponent = native = None
    try:
        if args.action == 'final':
            forbidden = ('--time-ms','--max-plies','--grace-ms','--seed','--elos','--subset','--bootstrap','--elo-step')
            if any(word.split('=')[0] in forbidden for word in sys.argv[1:]):
                raise ValueError('Final game settings come only from the reviewed frozen protocol; do not override them')
        stockfish_path = find_stockfish(args.stockfish)
        opponent = Stockfish(stockfish_path, args.hash_mb)
        if args.action == 'detect':
            text = json.dumps(opponent.metadata, indent=2)
            if args.output:
                if args.output.exists(): raise ValueError('Detection report already exists')
                atomic(args.output, text+'\n')
            print(text); return
        rows = load_openings(args.manifest)
        native = ChessAI(args.chessai)
        if args.action == 'final':
            if not args.protocol or not args.protocol_sha256: raise ValueError('Final requires a reviewed --protocol and --protocol-sha256')
            payload = read_frozen(args.protocol)
            if payload['protocol_sha256'] != args.protocol_sha256: raise ValueError('Reviewed protocol hash mismatch')
            protocol = payload['protocol']
            if protocol['purpose'] != 'final': raise ValueError('Not a final protocol')
            validate(protocol, rows, native.metadata, opponent.metadata, args.manifest)
        else:
            levels = [int(v) for v in args.elos.split(',')] if args.elos else None
            if args.action == 'smoke':
                if levels and len(levels) != 1: raise ValueError('Smoke accepts one strength only')
                levels = levels or [opponent.elo_min]
                rows = ordered(rows, args.seed)[:1]
            elif args.action == 'development':
                if not 2 <= args.subset < 64: raise ValueError('Development subset must be 2..63 opening pairs')
                levels = levels or ladder(opponent.elo_min, opponent.elo_max, args.elo_step)
                rows = ordered(rows, args.seed)[:args.subset]
            elif args.action == 'freeze':
                if not args.development: raise ValueError('Freeze requires completed --development bracketing results')
                development = json.loads(args.development.read_text())
                if not development['complete'] or not development['valid'] or development['protocol']['protocol']['purpose'] != 'development':
                    raise ValueError('A valid completed development calibration is required')
                previous = development['protocol']['protocol']
                if development['protocol']['protocol_sha256'] != digest(previous): raise ValueError('Development protocol hash mismatch')
                validate(previous, rows, native.metadata, opponent.metadata, args.manifest)
                if len(development['games']) != previous['games']: raise ValueError('Development game count mismatch')
                for played, planned in zip(development['games'], previous['plan']):
                    if any(played.get(key) != value for key, value in planned.items()) or played.get('invalid'):
                        raise ValueError('Development game order/completeness mismatch')
                recomputed = summary(development['games'], previous['seed'], infer=False)
                if (args.time_ms, args.max_plies, args.grace_ms) != (previous['move_time_ms'], previous['max_plies'], previous['response_grace_ms']):
                    raise ValueError('Final and development time control/adjudication must match')
                if not levels:
                    entries = recomputed['levels']
                    tested = sorted(int(v) for v in entries)
                    point, reason = crossing(tested, [entries[str(v)]['score_percent']/100 for v in tested])
                    if point is None: raise ValueError('Cannot select final strengths: '+reason)
                    levels = sorted(sorted(tested, key=lambda elo: (abs(elo-point), elo))[:4])
                    if len(levels) < 2: raise ValueError('Need multiple bracketing levels')
            protocol = build_protocol('final' if args.action == 'freeze' else args.action, rows, levels,
                                      native.metadata, opponent.metadata, args.manifest, args.seed,
                                      args.time_ms, args.max_plies, args.grace_ms, args.bootstrap)
            if args.action == 'freeze': protocol['development_results_sha256'] = sha256(args.development)
            default_protocol = 'calibration_protocol.json' if args.action == 'freeze' else args.action+'_protocol.json'
            payload = freeze(args.protocol or ROOT/default_protocol, protocol)
            print('Frozen protocol SHA-256:', payload['protocol_sha256'], flush=True)
            if args.action == 'freeze':
                print('No games run. Review the protocol before explicitly invoking final.'); return
        output = args.output or ROOT/('final_results.json' if args.action == 'final' else args.action+'_results.json')
        execute(payload, output, native, opponent)
    except (ValueError, OSError, EngineFault, KeyError) as exc:
        parser.exit(1, f'Calibration failed: {exc}\n')
    except KeyboardInterrupt:
        parser.exit(130, 'Interrupted: affected run is incomplete/invalid; do not selectively resume it.\n')
    finally:
        if native: native.close()
        if opponent: opponent.close()


if __name__ == '__main__': main()