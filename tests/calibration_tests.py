"""External calibration contracts: fake UCI engines, native adapter, no strength games."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import chess
from benchmarks.elo.transport import Stockfish, ChessAI, EngineFault, parse_option
from benchmarks.elo.openings import load_openings, normalized, ordered, schedule, ROOT
from benchmarks.elo.protocol import build_protocol, digest, freeze, read_frozen, validate, ladder
from benchmarks.elo.calibrate import play, termination, execute
from benchmarks.elo.calibration_stats import summary, crossing

FAKE = Path('tests/fake_calibration_uci.py')
NATIVE = Path('build/Release/ChessAI_calibration.exe')


def fake(*args, **kwargs):
    return Stockfish(FAKE, command=[sys.executable, str(FAKE), *args], **kwargs)


class UciTests(unittest.TestCase):
    def test_options(self):
        self.assertEqual(parse_option('option name UCI_Elo type spin default 777 min 777 max 999')['max'], 999)
        self.assertEqual(parse_option('option name Book Path type string default C:/some path/book')['default'], 'C:/some path/book')
        self.assertEqual(parse_option('option name Style type combo default Normal var Normal var Very Slow')['var'], ['Normal', 'Very Slow'])
        self.assertFalse(parse_option('option name Ponder type check default false')['default'])
        self.assertEqual(parse_option('option name Clear Hash type button')['type'], 'button')
        with self.assertRaises(ValueError): parse_option('invalid')

    def test_handshake_range_and_commands(self):
        with tempfile.TemporaryDirectory() as directory:
            log = Path(directory)/'uci.log'
            sf = fake('--min-elo', '777', '--max-elo', '999', '--log', str(log))
            try:
                self.assertEqual(sf.metadata['elo_range'], [777,999])
                self.assertEqual(sf.used['Threads'], 1)
                self.assertTrue(sf.used['UCI_LimitStrength'])
                self.assertEqual(sf.used['Hash'], 64)
                self.assertEqual(len(sf.metadata['binary_sha256']), 64)
                with self.assertRaises(ValueError): sf.newgame(1000)
                sf.newgame(800)
                board = chess.Board(); board.push_uci('e2e4')
                reply = sf.move(board, 25, 1000)
                self.assertIn(chess.Move.from_uci(reply['move']), board.legal_moves)
            finally: sf.close()
            text = log.read_text()
            self.assertIn('setoption name UCI_Elo value 800', text)
            self.assertIn('go movetime 25', text)
            self.assertIn(' moves e2e4', text)

    def test_missing_option_and_startup_errors(self):
        with self.assertRaisesRegex(ValueError, 'UCI_Elo'): fake('--mode', 'missing-elo')
        with self.assertRaises(EngineFault) as result: fake('--mode', 'startup-crash')
        self.assertEqual(result.exception.reason, 'engine_crash')
        with self.assertRaises(EngineFault) as result: fake('--mode', 'startup-timeout', handshake_timeout=.1)
        self.assertEqual(result.exception.reason, 'engine_timeout')

    def test_move_faults(self):
        for mode, reason in [('crash','engine_crash'), ('timeout','engine_timeout')]:
            sf = fake('--mode', mode)
            try:
                sf.newgame(1200)
                with self.assertRaises(EngineFault) as caught: sf.move(chess.Board(), 1, 100)
                self.assertEqual(caught.exception.reason, reason)
            finally: sf.close()


class RulesTests(unittest.TestCase):
    def test_endings(self):
        cases = [('7k/6Q1/6K1/8/8/8/8/8 b - - 0 1', ('1-0','checkmate')),
                 ('7k/5Q2/6K1/8/8/8/8/8 b - - 0 1', ('1/2-1/2','stalemate')),
                 ('7k/8/6K1/8/8/8/8/8 w - - 0 1', ('1/2-1/2','insufficient_material')),
                 ('7k/8/6K1/8/8/8/8/R7 w - - 100 51', ('1/2-1/2','fifty_move_rule')),
                 ('7k/6Q1/6K1/8/8/8/8/8 b - - 100 51', ('1-0','checkmate'))]
        for fen, expected in cases: self.assertEqual(termination(chess.Board(fen)), expected)
        board = chess.Board()
        for move in ['g1f3','g8f6','f3g1','f6g8']*2: board.push_uci(move)
        self.assertEqual(termination(board), ('1/2-1/2','repetition'))

    def test_native_moves_and_special_moves(self):
        native = ChessAI(NATIVE)
        try:
            self.assertEqual(native.metadata['alpha'], .25)
            for fen, special in [
                ('r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1', {'e1g1','e1c1'}),
                ('4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1', {'e5d6'}),
                ('4k3/P7/8/8/8/8/8/4K3 w - - 0 1', {'a7a8q','a7a8r','a7a8b','a7a8n'}),
                ('4k3/8/8/8/8/8/p7/4K3 b - - 0 1', {'a2a1q','a2a1n'})]:
                board = chess.Board(fen)
                native.transport.send('legal\t'+fen)
                legal = set(native.reply(5)['moves'])
                self.assertEqual(legal, {move.uci() for move in board.legal_moves})
                self.assertTrue(special <= legal)
                native.newgame()
                result = native.move(board, 5, 1000)
                self.assertIn(result['move'], legal)
                self.assertGreaterEqual(result['search_ms'], 0)
        finally: native.close()

    def test_all_external_positions_agree_with_native_legality(self):
        native = ChessAI(NATIVE)
        try:
            for row in load_openings():
                native.transport.send('legal\t'+row['fen'])
                self.assertEqual(set(native.reply(5)['moves']), {m.uci() for m in chess.Board(row['fen']).legal_moves}, row['id'])
        finally: native.close()


class SuiteTests(unittest.TestCase):
    def test_legal_frozen_unique_and_pairing(self):
        rows = load_openings()
        self.assertEqual(hashlib.sha256((ROOT/'openings-v1.tsv').read_bytes()).hexdigest(),
                         '58520f80a735353a7366d782b38af9ce246110b1ee4c55a6f422fb400f60490e')
        self.assertEqual(len(rows), 64)
        self.assertGreaterEqual(len({r['family'] for r in rows}), 20)
        self.assertEqual(len({normalized(chess.Board(r['fen'])) for r in rows}), 64)
        self.assertEqual(ordered(rows, 42), ordered(rows, 42))
        self.assertNotEqual(ordered(rows, 42), ordered(rows, 43))
        plan = schedule(rows, [1200, 1400], 42)
        self.assertEqual(len(plan), 256)
        for a,b in zip(plan[::2], plan[1::2]):
            self.assertEqual(a['opening_id'], b['opening_id'])
            self.assertEqual(a['opponent_elo'], b['opponent_elo'])
            self.assertEqual((a['chessai_color'],b['chessai_color']), ('white','black'))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'bad.tsv'; path.write_bytes((ROOT/'openings-v1.tsv').read_bytes()+b'\n')
            with self.assertRaisesRegex(ValueError, 'hash'): load_openings(path)
        self.assertEqual(ladder(777,999,200), [777,977,999])

    def test_no_internal_endpoint_overlap(self):
        external = {normalized(chess.Board(r['fen'])) for r in load_openings()}
        for path in Path('benchmarks/suites').glob('*.tsv'):
            internal = {normalized(chess.Board(line.split('\t')[2]+' 0 1')) for line in path.read_text().splitlines()[1:]}
            self.assertFalse(external & internal)


class StatisticsTests(unittest.TestCase):
    def test_accounting_and_cluster_bootstrap(self):
        games = []
        # Paired perfect correlation: independent-game bootstrap would give a narrower interval.
        for opening, result in [('a',1), ('b',0)]:
            for color in ('white','black'):
                games.append({'opening_id':opening,'chessai_color':color,'opponent_elo':1200,'plies':100,
                              'result':'1-0' if (color=='white') == bool(result) else '0-1', 'termination':'checkmate'})
        stats = summary(games,42,1000)
        level = stats['levels']['1200']
        self.assertEqual((level['wins'],level['draws'],level['losses']), (2,0,2))
        self.assertEqual(level['score_percent'], 50)
        self.assertEqual(level['score_ci95_percent'], [0,100])
        self.assertEqual(level['by_color']['black']['score_percent'], 50)
        self.assertIsNone(stats['calibration']['estimate'])
        self.assertEqual(stats, summary(games,42,1000))
        with self.assertRaises(ValueError): summary(games[:-1],42,100)

    def test_interpolation_and_no_invented_estimate(self):
        self.assertEqual(crossing([1000,1200],[.75,.25]), (1100,None))
        for values in ([.9,.6], [.3,.1], [.4,.6], [.5,.5]): self.assertIsNone(crossing([1000,1200],values)[0])
        games = []
        for i in range(8):
            for elo, outcomes in [(1000,('1-0','1/2-1/2')), (1200,('1/2-1/2','1-0'))]:
                for color, outcome in zip(('white','black'),outcomes):
                    games.append({'opening_id':str(i),'opponent_elo':elo,'chessai_color':color,
                                  'result':outcome,'termination':'checkmate','plies':60})
        result = summary(games,3,1000)['calibration']
        self.assertEqual(result['estimate'],1100)
        self.assertEqual(result['ci95'],[1100,1100])


class ProtocolAndMatchTests(unittest.TestCase):
    def setUp(self):
        self.native = ChessAI(NATIVE)
        self.opponent = fake()
        self.rows = load_openings()

    def tearDown(self):
        self.native.close(); self.opponent.close()

    def protocol(self, phase='smoke'):
        return build_protocol(phase,self.rows[:1],[1200],self.native.metadata,self.opponent.metadata,
                              ROOT/'openings-v1.tsv', time_ms=1,max_plies=14,bootstrap=100)

    def test_freeze_tamper_and_environment(self):
        protocol = self.protocol()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'protocol.json'
            payload = freeze(path,protocol)
            self.assertEqual(read_frozen(path), payload)
            with self.assertRaises(ValueError): freeze(path,protocol)
            validate(protocol,self.rows,self.native.metadata,self.opponent.metadata,ROOT/'openings-v1.tsv')
            for field in ('implementation_sha256','manifest_sha256'):
                bad = copy.deepcopy(protocol); bad[field] = 'bad'
                with self.assertRaises(ValueError): validate(bad,self.rows,self.native.metadata,self.opponent.metadata,ROOT/'openings-v1.tsv')
            bad = copy.deepcopy(protocol); bad['chessai']['binary_sha256'] = 'bad'
            with self.assertRaises(ValueError): validate(bad,self.rows,self.native.metadata,self.opponent.metadata,ROOT/'openings-v1.tsv')
            path.write_text(path.read_text()+' ')
            with self.assertRaises(ValueError): read_frozen(path)
        with self.assertRaises(ValueError): self.protocol('final')

    def test_paired_legal_smoke(self):
        protocol = self.protocol()
        with tempfile.TemporaryDirectory() as folder:
            report = execute({'protocol':protocol,'protocol_sha256':digest(protocol)},Path(folder)/'smoke.json',self.native,self.opponent)
            self.assertTrue(report['complete'] and report['valid'])
            self.assertEqual(len(report['games']), 2)
            for game in report['games']:
                board = chess.Board()
                for move in game['forced_moves']+game['moves']: board.push_uci(move)
                self.assertEqual(board.fen(en_passant='fen'),game['final_fen'])
                self.assertEqual(game['termination'],'max_ply_draw')
                self.assertEqual(len(game['move_timings']),game['searched_plies'])
            with self.assertRaises(ValueError): execute({'protocol':protocol},Path(folder)/'smoke.json',self.native,self.opponent)

    def test_fault_invalidates_entire_run(self):
        self.opponent.close(); self.opponent = fake('--mode','illegal')
        protocol = self.protocol()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'invalid.json'
            with self.assertRaises(EngineFault): execute({'protocol':protocol,'protocol_sha256':digest(protocol)},path,self.native,self.opponent)
            report = json.loads(path.read_text())
            self.assertFalse(report['valid']); self.assertFalse(report['complete'])
            self.assertEqual(report['games'][0]['termination'],'illegal_move')
            self.assertEqual(len(report['games']),1)
            self.assertIsNone(report['summary']['calibration']['estimate'])

    def test_crash_and_timeout_game_accounting(self):
        for mode, reason in [('crash','engine_crash'), ('timeout','engine_timeout')]:
            self.opponent.close(); self.opponent = fake('--mode',mode)
            config = self.protocol(); config['response_grace_ms'] = 100
            record = dict(config['plan'][0])
            play(record,self.rows[0],self.native,self.opponent,config)
            self.assertTrue(record['invalid'])
            self.assertEqual(record['termination'],reason)
            self.assertEqual(record['fault_engine'],'stockfish')
            self.assertEqual(record['result'],'1-0')

    def test_final_plan_freezes_all_positions_and_color_pairs(self):
        config = build_protocol('final',self.rows,[1200,1400,1600,1800],self.native.metadata,self.opponent.metadata,
                                ROOT/'openings-v1.tsv')
        self.assertEqual(config['games'],512)
        validate(config,self.rows,self.native.metadata,self.opponent.metadata,ROOT/'openings-v1.tsv')
        bad = copy.deepcopy(config); bad['plan'][0]['chessai_color'] = 'black'
        with self.assertRaises(ValueError): validate(bad,self.rows,self.native.metadata,self.opponent.metadata,ROOT/'openings-v1.tsv')

    def test_interruption_cannot_publish_valid_estimate(self):
        config = self.protocol()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'interrupted.json'
            with patch.object(self.native,'move',side_effect=KeyboardInterrupt), self.assertRaises(KeyboardInterrupt):
                execute({'protocol':config,'protocol_sha256':digest(config)},path,self.native,self.opponent)
            result = json.loads(path.read_text())
            self.assertFalse(result['complete']); self.assertFalse(result['valid'])
            self.assertEqual(result['games'][0]['termination'],'interrupted')
            self.assertIsNone(result['summary']['calibration']['estimate'])

    def test_cli_missing_stockfish_fails_clearly(self):
        process = subprocess.run([sys.executable,'benchmarks/elo/calibrate.py','detect','--stockfish','missing-stockfish.exe'],
                                 capture_output=True,text=True)
        self.assertNotEqual(process.returncode,0)
        self.assertIn('Stockfish executable not found',process.stderr)


if __name__ == '__main__': unittest.main()
