"""Publish a clearly labelled two-game FAKE-UCI integration artifact, never a strength estimate."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from benchmarks.elo.calibrate import execute
from benchmarks.elo.openings import ROOT, load_openings
from benchmarks.elo.protocol import build_protocol, freeze
from benchmarks.elo.transport import ChessAI, Stockfish

native = ChessAI('build/Release/ChessAI_calibration.exe')
opponent = None
try:
    opponent = Stockfish('tests/fake_calibration_uci.py', command=[sys.executable, 'tests/fake_calibration_uci.py'])
    protocol = build_protocol('test_fixture',load_openings()[:1],[1200],native.metadata,opponent.metadata,
                              ROOT/'openings-v1.tsv',time_ms=5,max_plies=14,bootstrap=100)
    protocol['label'] = 'FAKE UCI TEST FIXTURE — NOT A STOCKFISH CALIBRATION'
    payload = freeze(ROOT/'fixture_smoke_protocol.json',protocol)
    execute(payload,ROOT/'fixture_smoke_results.json',native,opponent)
finally:
    native.close()
    if opponent: opponent.close()
