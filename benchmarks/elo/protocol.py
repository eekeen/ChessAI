"""Create-once protocol files, source/binary binding and explicit final-phase validation."""
import hashlib
import json
from pathlib import Path
import platform
import sys
import chess
from benchmarks.elo.openings import ROOT, ordered, schedule
from benchmarks.elo.transport import sha256


def canonical(value): return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
def digest(value): return hashlib.sha256(canonical(value)).hexdigest()


def implementation_hash():
    names = ('transport.py', 'calibration_stats.py', 'openings.py', 'protocol.py', 'calibrate.py')
    return digest({name: sha256(ROOT/name) for name in names})


def ladder(low, high, step=200):
    if low >= high or step < 1: raise ValueError('Invalid Elo ladder bounds/spacing')
    return sorted(set([*range(low, high+1, step), high]))


def build_protocol(phase, rows, levels, chessai, stockfish, manifest, seed=20260926,
                   time_ms=250, max_plies=300, grace_ms=2000, bootstrap=5000):
    if time_ms < 1 or max_plies < 13 or grace_ms < 1 or bootstrap < 100: raise ValueError('Invalid protocol limits')
    if not levels or len(set(levels)) != len(levels): raise ValueError('Distinct opponent levels required')
    low, high = stockfish['elo_range']
    if any(not low <= elo <= high for elo in levels): raise ValueError(f'UCI_Elo must be in [{low}, {high}]')
    if phase == 'final' and (len(rows) != 64 or len(levels) < 2):
        raise ValueError('Final calibration requires all 64 openings and multiple opponent strengths')
    result = {'format': 1, 'purpose': phase, 'label': 'Stockfish UCI_Elo calibrated under this exact move-time protocol',
              'manifest_sha256': sha256(manifest), 'manifest_version': 'external-calibration-openings-v1',
              'chessai': chessai, 'stockfish': stockfish, 'levels': sorted(levels),
              'model': chessai['model'], 'alpha': chessai['alpha'], 'seed': seed,
              'move_time_ms': time_ms, 'response_grace_ms': grace_ms, 'max_plies': max_plies,
              'bootstrap_iterations': bootstrap, 'openings': ordered(rows, seed),
              'plan': schedule(rows, levels, seed), 'implementation_sha256': implementation_hash(),
              'python': sys.version, 'python_chess': chess.__version__,
              'rules': {'draws': 'automatic claim on actual third repetition or halfmove_clock >= 100; mate/stalemate take precedence',
                        'insufficient_material': 'python-chess conservative detection',
                        'max_plies': 'draw; count includes forced opening moves',
                        'fault': 'forfeit recorded, entire run invalidated and stopped; no selective replay',
                        'adjudication': 'no evaluation-based adjudication',
                        'tt': 'both cleared before each game; retained between moves within a game',
                        'ponder': False, 'book': 'only the same forced opening for both engines'},
              'ordering': 'seeded SHA256 opening order, rotated seeded level order, consecutive swapped-color pairs'}
    result['games'] = len(result['plan'])
    return result


def freeze(path, protocol):
    path = Path(path)
    sidecar = Path(str(path)+'.sha256')
    if path.exists() or sidecar.exists(): raise ValueError('Protocol already exists: frozen files are never overwritten')
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {'protocol_sha256': digest(protocol), 'protocol': protocol}
    encoded = json.dumps(payload, indent=2, allow_nan=False)+'\n'
    # Exclusive creation. A crash before the seal is written leaves an unusable protocol.
    with path.open('x', encoding='utf-8', newline='\n') as stream: stream.write(encoded)
    with sidecar.open('x', encoding='ascii') as stream: stream.write(sha256(path)+'\n')
    return payload


def read_frozen(path):
    path = Path(path)
    if sha256(path) != Path(str(path)+'.sha256').read_text().strip(): raise ValueError('Protocol file seal mismatch')
    payload = json.loads(path.read_text(encoding='utf-8'))
    if digest(payload['protocol']) != payload['protocol_sha256']: raise ValueError('Protocol content hash mismatch')
    return payload


def validate(protocol, rows, chessai, stockfish, manifest):
    if protocol['implementation_sha256'] != implementation_hash(): raise ValueError('Harness changed after protocol freeze')
    if protocol['python_chess'] != chess.__version__ or protocol['python'] != sys.version:
        raise ValueError('Python environment changed after protocol freeze')
    if protocol['manifest_sha256'] != sha256(manifest): raise ValueError('Opening manifest changed after freeze')
    available = {r['id']: r for r in rows}
    if any(available.get(r['id']) != r for r in protocol['openings']): raise ValueError('Protocol opening content mismatch')
    if protocol['plan'] != schedule(protocol['openings'], protocol['levels'], protocol['seed']):
        raise ValueError('Frozen game order/pairing mismatch')
    if protocol['games'] != len(protocol['plan']): raise ValueError('Frozen game count mismatch')
    if protocol['purpose'] == 'final' and (len(protocol['openings']) != 64 or len(protocol['levels']) < 2):
        raise ValueError('Incomplete final protocol')
    for name, actual in [('chessai', chessai), ('stockfish', stockfish)]:
        if protocol[name] != actual: raise ValueError(f'{name} binary/metadata/options changed after freeze')


def machine():
    result = {'platform': platform.platform(), 'processor': platform.processor(), 'python': sys.version}
    if sys.platform == 'win32':
        import subprocess
        try:
            result['cpu'] = subprocess.check_output(['powershell', '-NoProfile', '-Command',
                '(Get-CimInstance Win32_Processor).Name'], text=True, timeout=15).strip()
        except (OSError, subprocess.SubprocessError): result['cpu'] = platform.processor()
    return result
