"""Create deliberately synthetic pipeline-test data, never a playing-strength dataset."""
import argparse
import json
from pathlib import Path
import random
import zstandard


def example_records(count=700, seed=42):
    rng = random.Random(seed)
    scores = [-1200, -500, -200, 0, 200, 500, 1200]
    for i in range(count):
        squares = [""] * 64
        squares[4], squares[60] = "K", "k"
        for square in rng.sample([s for s in range(8, 56)], rng.randrange(3, 25)):
            squares[square] = rng.choice("PNBRQpnbrq")
        ranks = []
        for rank in range(7, -1, -1):
            text, empty = "", 0
            for piece in squares[rank * 8:rank * 8 + 8]:
                if piece:
                    text += (str(empty) if empty else "") + piece
                    empty = 0
                else:
                    empty += 1
            ranks.append(text + (str(empty) if empty else ""))
        fen = "/".join(ranks) + (" w" if i % 2 else " b") + " - -"
        yield {"fen": fen, "evals": [{"depth": 10, "knodes": 10, "pvs": [{"cp": 1}]},
                                         {"depth": 20, "knodes": 100, "pvs": [{"cp": scores[i % 7]}]}]}


def write_example(path, count=700):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    records = list(example_records(count))
    lines = [json.dumps(r) for r in records + records[:10]] + ["{bad", "null", "{}"]
    path.write_bytes(zstandard.ZstdCompressor().compress(("\n".join(lines) + "\n").encode()))
    print(f"Wrote {path}: synthetic labels/positions for software testing only")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="ml/data/example.jsonl.zst")
    parser.add_argument("--count", type=int, default=700)
    args = parser.parse_args()
    write_example(args.output, args.count)
