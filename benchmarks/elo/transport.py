"""Bounded line transports and strict Stockfish UCI option negotiation."""
import hashlib
import json
from pathlib import Path
import queue
import re
import subprocess
import threading
import time
import chess


class EngineFault(RuntimeError):
    def __init__(self, reason, message):
        super().__init__(message)
        self.reason = reason


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Process:
    def __init__(self, command):
        try:
            self.process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                            stderr=subprocess.DEVNULL, text=True, bufsize=1)
        except OSError as exc:
            raise EngineFault('engine_crash', f'Cannot start {command[0]}: {exc}') from exc
        self.lines = queue.Queue()
        def read():
            try:
                for line in self.process.stdout:
                    self.lines.put(line.strip())
            finally:
                self.lines.put(None)
        self.reader = threading.Thread(target=read, daemon=True)
        self.reader.start()

    def send(self, command):
        try:
            self.process.stdin.write(command + '\n')
            self.process.stdin.flush()
        except (OSError, ValueError) as exc:
            raise EngineFault('engine_crash', 'Engine closed its input') from exc

    def receive(self, deadline):
        remaining = deadline - time.monotonic()
        if remaining <= 0: raise EngineFault('engine_timeout', 'Engine response deadline expired')
        try:
            line = self.lines.get(timeout=remaining)
        except queue.Empty as exc:
            raise EngineFault('engine_timeout', 'Engine response deadline expired') from exc
        if line is None: raise EngineFault('engine_crash', 'Engine exited before completing its response')
        return line

    def until(self, token, seconds=15):
        deadline = time.monotonic() + seconds
        lines = []
        while True:
            line = self.receive(deadline)
            lines.append(line)
            if line.split()[:1] == [token]: return lines
            if len(lines) > 10000: raise EngineFault('protocol_error', 'Excessive handshake output')

    def close(self):
        if self.process.poll() is None:
            self.process.kill()
        self.process.wait()
        self.reader.join(timeout=2)
        self.process.stdin.close()
        self.process.stdout.close()


def parse_option(line):
    match = re.fullmatch(r'option name (.+?) type (spin|check|button|combo|string)(?: (.*))?', line)
    if not match: raise ValueError('Malformed UCI option: ' + line)
    name, kind, rest = match.groups()
    option = {'name': name, 'type': kind, 'raw': line}
    parts = re.split(r'(?:^| )(default|min|max|var)(?: |$)', rest or '')
    for key, value in zip(parts[1::2], parts[2::2]):
        value = value.strip()
        if key == 'var': option.setdefault('var', []).append(value)
        elif key in ('min', 'max') or (key == 'default' and kind == 'spin'): option[key] = int(value)
        elif key == 'default' and kind == 'check':
            if value not in ('true', 'false'): raise ValueError('Invalid UCI check default')
            option[key] = value == 'true'
        else: option[key] = value
    return option


class Stockfish:
    def __init__(self, executable, hash_mb=64, command=None, handshake_timeout=15):
        self.transport = Process(command or [str(Path(executable).resolve())])
        try:
            self.transport.send('uci')
            lines = self.transport.until('uciok', handshake_timeout)
            self.options = {}
            for line in lines:
                if line.startswith('option '):
                    option = parse_option(line)
                    self.options[option['name']] = option
            for name, kind in [('UCI_LimitStrength', 'check'), ('UCI_Elo', 'spin'), ('Threads', 'spin'), ('Hash', 'spin')]:
                if self.options.get(name, {}).get('type') != kind:
                    raise ValueError(f'Stockfish must expose {name} ({kind})')
            self.elo_min, self.elo_max = self.options['UCI_Elo']['min'], self.options['UCI_Elo']['max']
            if self.elo_min >= self.elo_max: raise ValueError('Invalid advertised UCI_Elo range')
            self.used = {}
            self.set_option('Threads', 1)
            self.set_option('Hash', hash_mb)
            self.set_option('UCI_LimitStrength', True)
            for name, value in [('Ponder', False), ('MultiPV', 1), ('UCI_Chess960', False),
                                ('Move Overhead', 0), ('nodestime', 0), ('SyzygyPath', '')]:
                if name in self.options: self.set_option(name, value)
            if 'Skill Level' in self.options: self.set_option('Skill Level', self.options['Skill Level']['max'])
            self.ready()
            name = next((s[8:] for s in lines if s.startswith('id name ')), '')
            if 'stockfish' not in name.lower(): raise ValueError('UCI engine does not identify itself as Stockfish')
            self.metadata = {'name': next((s[8:] for s in lines if s.startswith('id name ')), 'unknown'),
                             'id_lines': [s for s in lines if s.startswith('id ')],
                             'binary_sha256': sha256(executable), 'elo_range': [self.elo_min, self.elo_max],
                             'supported_options': self.options, 'options_used': dict(self.used)}
        except BaseException:
            self.close()
            raise

    def set_option(self, name, value=None):
        option = self.options[name]
        if option['type'] == 'spin' and (not isinstance(value, int) or not option['min'] <= value <= option['max']):
            raise ValueError(f'{name} must be in [{option["min"]}, {option["max"]}]')
        if option['type'] == 'check' and not isinstance(value, bool): raise ValueError('Expected boolean')
        rendered = str(value).lower() if isinstance(value, bool) else str(value)
        self.transport.send(f'setoption name {name}' + ('' if option['type'] == 'button' else f' value {rendered}'))
        self.used[name] = value

    def ready(self):
        self.transport.send('isready')
        self.transport.until('readyok')

    def newgame(self, elo):
        self.set_option('UCI_Elo', elo)
        self.transport.send('ucinewgame')
        if 'Clear Hash' in self.options: self.set_option('Clear Hash')
        self.ready()

    def move(self, board, budget_ms, grace_ms):
        # Full history, including the forced opening, preserves repetition context.
        root = board.root().fen(en_passant='fen')
        moves = ' '.join(move.uci() for move in board.move_stack)
        position = 'position startpos' if root == chess.STARTING_FEN else 'position fen ' + root
        self.transport.send(position + (' moves ' + moves if moves else ''))
        start = time.monotonic()
        self.transport.send(f'go movetime {budget_ms}')
        deadline = start + (budget_ms + grace_ms)/1000
        info = {}
        while True:
            line = self.transport.receive(deadline)
            tokens = line.split()
            if tokens[:1] == ['info']:
                for field in ('time', 'nodes', 'depth'):
                    if field in tokens:
                        try: info[field] = int(tokens[tokens.index(field)+1])
                        except (ValueError, IndexError): pass
            if tokens[:1] == ['bestmove']:
                if len(tokens) < 2: raise EngineFault('protocol_error', 'Missing UCI bestmove')
                return {'move': tokens[1], 'response_ms': 1000*(time.monotonic()-start),
                        'search_ms': info.get('time'), 'nodes': info.get('nodes'), 'depth': info.get('depth')}

    def close(self): self.transport.close()


class ChessAI:
    def __init__(self, executable):
        self.transport = Process([str(Path(executable).resolve())])
        try:
            self.transport.send('hello')
            self.metadata = self.reply(15)
            if (self.metadata.get('model') != 'v2-residual-3fb0a29e8514af8c' or
                self.metadata.get('alpha') != .25 or self.metadata.get('mode') != 'hybrid' or
                self.metadata.get('build') != 'Release' or self.metadata.get('protocol') != 1):
                raise ValueError('Calibration adapter is not the frozen production Hybrid V2 configuration')
            self.metadata['binary_sha256'] = sha256(executable)
        except BaseException:
            self.close()
            raise

    def reply(self, timeout):
        try: return json.loads(self.transport.receive(time.monotonic()+timeout))
        except (ValueError, TypeError) as exc: raise EngineFault('protocol_error', 'Invalid adapter JSON') from exc

    def newgame(self):
        self.transport.send('newgame')
        if self.reply(15).get('type') != 'ready': raise EngineFault('protocol_error', 'Missing newgame acknowledgment')

    def move(self, board, budget_ms, grace_ms):
        start = time.monotonic()
        self.transport.send(f'search {budget_ms}\t{board.fen(en_passant="fen")}')
        result = self.reply((budget_ms+grace_ms)/1000)
        if result.get('type') != 'move': raise EngineFault('protocol_error', 'Missing adapter move')
        result['response_ms'] = 1000*(time.monotonic()-start)
        return result

    def close(self): self.transport.close()
