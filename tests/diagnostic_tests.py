"""Metrics and native diagnostic regression tests (no model training)."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
from diagnostic_metrics import rank_metrics, clipping_pairs, corrections, stability
from diagnose_evaluators import native, markdown
from stockfish_labels import parse_score, Stockfish


class MetricsTests(unittest.TestCase):
    def test_perspective_and_regret(self):
        white = rank_metrics([30, 20, 10], [0, 100, -50], "w")
        black = rank_metrics([30, 20, 10], [0, 100, -50], "b")
        self.assertEqual(white["regret_cp"], 100)
        self.assertEqual(black["regret_cp"], 0)
        self.assertEqual(white["top1"], 0)
        self.assertEqual(black["top1"], 1)
        self.assertAlmostEqual(white["pairwise_accuracy"], 2/3)
        self.assertAlmostEqual(white["spearman"], .5)

    def test_ties(self):
        m = rank_metrics([0, 0, 0], [0, 100, -50], "w")
        self.assertEqual(m["pairwise_accuracy"], .5)
        self.assertAlmostEqual(m["top1_uniform_tie_expectation"], 1/3)
        self.assertIsNone(m["spearman"])
        self.assertIsNone(rank_metrics([1, 2], [1, 1], "w")["pairwise_accuracy"])
        self.assertEqual(rank_metrics([10, 9, 8, 7], [0, 0, 0, 1], "w")["top3_contains_target_best"], 0)

    def test_clipping_attribution(self):
        parents = [{"children": [{"raw": x} for x in (1600, 1800, 0, 0)]}]
        self.assertEqual(clipping_pairs(parents, "raw", 0)["new_tied_pairs"], 1)
        self.assertEqual(clipping_pairs(parents, "raw", 5)["pairs"], 6)
        parents = [{"children": [{"raw": x} for x in (1498, 1700)]}]
        self.assertEqual(clipping_pairs(parents, "raw", 0)["new_tied_pairs"], 0)
        self.assertEqual(clipping_pairs(parents, "raw", 5)["new_tied_pairs"], 1)

    def test_signed_correction(self):
        r = corrections([{"classic": 50, "hybrid": -100, "residual_raw": -150},
                         {"classic": 2000, "hybrid": 1500, "residual_raw": 500}])
        self.assertEqual(r["raw_residual"]["all"]["sign_flip_percent"], 50)
        self.assertEqual(r["raw_residual"]["1500_to_inf"]["mean"], 500)
        self.assertEqual(r["deployed_hybrid_minus_classic"]["1500_to_inf"]["mean"], -500)

    def test_uci_cp_and_mate(self):
        self.assertEqual(parse_score("info depth 12 score cp 75 pv e7e5", "b")["cp_white"], -75)
        self.assertEqual(parse_score("info depth 12 score mate -3 pv e2e4", "b")["mate_white"], 3)
        self.assertIsNone(parse_score("info depth 12 score cp 75 lowerbound", "w"))
        self.assertIsNone(parse_score("info depth 12 multipv 2 score cp 75", "w"))

    def test_uci_session(self):
        # A clearly synthetic protocol fixture; never a source of benchmark labels.
        source = '''import sys
for line in sys.stdin:
    command = line.strip()
    if command == "uci":
        print("id name TEST ONLY UCI stub", flush=True)
        print("uciok", flush=True)
    elif command == "isready":
        print("readyok", flush=True)
    elif command.startswith("go depth"):
        print("info depth 12 score cp 50 pv e7e5", flush=True)
        print("info depth 12 score cp 90 lowerbound", flush=True)
        print("bestmove e7e5", flush=True)
'''
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"uci_stub.py"
            path.write_text(source)
            real_popen = subprocess.Popen
            def launch(command, **kwargs):
                return real_popen([sys.executable, str(path)], **kwargs)
            with patch("stockfish_labels.subprocess.Popen", side_effect=launch):
                engine = Stockfish(path, depth=12, timeout=5)
                try:
                    self.assertEqual(engine.evaluate("4k3/8/8/8/8/8/8/4K3 b - - 0 1")["cp_white"], -50)
                    self.assertEqual(engine.evaluate("4k3/8/8/8/8/8/8/4K3 w - - 0 1")["cp_white"], 50)
                    self.assertEqual(engine.metadata["threads"], 1)
                finally:
                    engine.close()


class NativeTests(unittest.TestCase):
    def test_logging_preserves_search_and_sampling(self):
        fens = ["rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
                "4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1",
                "4k3/P7/8/8/8/8/8/4K3 w - - 0 1"]
        options = ("--children", "--leaf-roots", 3, "--leaf-samples", 20)
        a = native(Path("build/Release/ChessAI_diagnostics.exe"), fens, options)
        b = native(Path("build/Release/ChessAI_diagnostics.exe"), fens, options)
        self.assertEqual(a, b)
        reference = subprocess.run(["build/Release/eval_tool.exe", "search-diagnostic-reference"],
                                   input="\n".join(fens)+"\n", text=True, capture_output=True, check=True)
        actual = [f"{r['root']} {r['mode']} {r['nodes']} {r['score']} {r['bestmove']}"
                  for r in a if r["type"] == "search"]
        self.assertEqual(actual, reference.stdout.splitlines())
        parents = [r for r in a if r["type"] == "parent"]
        self.assertEqual([p["parent"]["fen"] for p in parents], fens)
        for p in parents:
            for child in p["children"]:
                self.assertNotEqual(child["side"], p["parent"]["side"])
        ep = next(c for c in parents[1]["children"] if c["move"] == "e5d6")
        self.assertTrue(ep["capture"])
        self.assertEqual(sum(c["promotion"] for c in parents[2]["children"]), 4)
        leaves = [r for r in a if r["type"] == "leaf"]
        self.assertEqual(len(leaves), 60)
        self.assertTrue(all(0 <= r["ply"] <= 64 for r in leaves))
        self.assertTrue(all(r["incoming"] in (0, 1) for r in leaves))

    def test_report_pipeline_fixture(self):
        # Explicit test-only labels, never used in the real diagnostic report.
        fen = "4k3/8/8/8/8/8/8/4K3 w - - 0 1"
        records = native(Path("build/Release/ChessAI_diagnostics.exe"), [fen], ("--children",))
        children = next(r["children"] for r in records if r["type"] == "parent")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dataset = root/"fixture.npz"
            np.savez(dataset, fen=[fen]+[c["fen"] for c in children], y=[0]+list(range(len(children))),
                     split=[2]+[0]*len(children), metadata=json.dumps({"target_perspective": "white", "clip_cp": 1500}))
            output = root/"report.json"
            subprocess.run([sys.executable, "benchmarks/diagnose_evaluators.py", "--data", str(dataset),
                            "--parents", "1", "--leaf-roots", "0", "--output", str(output)], check=True, capture_output=True)
            result = json.loads(output.read_text())
            self.assertEqual(result["ranking"]["complete_cp_parents"], 1)
            self.assertEqual(result["ranking"]["cached_children"], len(children))
            self.assertTrue(output.with_suffix(".md").exists())
            self.assertNotIn("NaN", output.read_text())


if __name__ == "__main__":
    unittest.main()
