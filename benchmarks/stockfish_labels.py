"""Optional installed UCI engine. No downloads and no synthetic mate-to-cp labels."""
import hashlib
import queue
import subprocess
import threading
import time
from pathlib import Path


def parse_score(line, side):
    words = line.split()
    if not words or words[0] != "info" or "score" not in words:
        return None
    if "lowerbound" in words or "upperbound" in words:
        return None
    if "multipv" in words and words[words.index("multipv")+1] != "1":
        return None
    i = words.index("score")
    kind, value = words[i+1], int(words[i+2])
    if kind not in ("cp", "mate"):
        return None
    return {kind + "_white": value * (1 if side == "w" else -1),
            "depth": int(words[words.index("depth")+1]) if "depth" in words else None}


class Stockfish:
    def __init__(self, executable, depth=12, timeout=120):
        self.depth, self.timeout = depth, timeout
        self.process = subprocess.Popen([str(Path(executable).resolve())], stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        self.lines = queue.Queue()
        def read():
            for line in self.process.stdout:
                self.lines.put(line.strip())
            self.lines.put(None)
        threading.Thread(target=read, daemon=True).start()
        try:
            self.send("uci")
            startup = self.until("uciok")
            self.metadata = {"id": [s for s in startup if s.startswith("id ")],
                             "executable_sha256": hashlib.sha256(Path(executable).read_bytes()).hexdigest(),
                             "depth": depth, "threads": 1, "hash_mb": 64, "perspective": "white"}
            for option in ("Threads value 1", "Hash value 64", "MultiPV value 1", "UCI_LimitStrength value false"):
                self.send("setoption name " + option)
            self.send("isready")
            self.until("readyok")
        except BaseException:
            self.close()
            raise

    def send(self, command):
        self.process.stdin.write(command + "\n")
        self.process.stdin.flush()

    def until(self, prefix):
        deadline, output = time.monotonic() + self.timeout, []
        while True:
            try:
                line = self.lines.get(timeout=max(.001, deadline-time.monotonic()))
            except queue.Empty:
                raise TimeoutError("UCI engine timed out waiting for " + prefix)
            if line is None:
                raise RuntimeError("UCI engine exited before " + prefix)
            output.append(line)
            if line.startswith(prefix):
                return output

    def evaluate(self, fen):
        # Reset per child, so label search is independent of earlier children.
        self.send("ucinewgame")
        self.send("isready")
        self.until("readyok")
        self.send("position fen " + fen)
        self.send("go depth " + str(self.depth))
        score = None
        for line in self.until("bestmove"):
            parsed = parse_score(line, fen.split()[1])
            if parsed is not None:
                score = parsed
        return score

    def close(self):
        if self.process.poll() is None:
            self.process.kill()
        self.process.wait()
        if self.process.stdin:
            self.process.stdin.close()
        if self.process.stdout:
            self.process.stdout.close()
