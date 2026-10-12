"""Performance accounting/integration checks, not strength experiments."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
from benchmark_performance import summarize


class PerformanceTests(unittest.TestCase):
    def test_accounting(self):
        rows = []
        for mode, elapsed in (("classic", 1), ("ml", 2), ("hybrid", 3)):
            rows.append({"type": "static", "mode": mode, "evaluations": 1000, "elapsed_ms": elapsed})
            for p, (nodes, ms, depth) in enumerate(((100, 10, 2), (900, 90, 4))):
                rows.append({"type": "search", "mode": mode, "budget_ms": 100, "nodes": nodes,
                             "elapsed_ms": ms, "completed_depth": depth, "position": p, "tt_hits": 5, "score": 0})
        result = summarize(rows)
        self.assertEqual(result["static"]["hybrid"]["slowdown_vs_classic"], 3)
        self.assertEqual(result["static"]["classic"]["evaluations_per_second"], 1000000)
        m = result["search"]["100"]["hybrid"]
        self.assertEqual(m["completed_depth"]["mean"], 3)
        self.assertEqual(m["nodes_per_second"], 10000)
        self.assertEqual(m["total_nodes"], 1000)
        self.assertEqual(m["tt_hits"], 10)

    def test_native_smoke(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/"performance.json"
            cmd = [sys.executable, "benchmarks/benchmark_performance.py", "--repetitions", "1",
                   "--evaluations", "1000", "--warmup", "100", "--budgets", "1", "--output", str(output)]
            subprocess.run(cmd, check=True, capture_output=True, timeout=60)
            report = json.loads(output.read_text(encoding="utf-8"))
            meta = report["native_metadata"]
            self.assertEqual(meta["hybrid_alpha"], .25)
            self.assertEqual(meta["positions"], 16)
            self.assertEqual(meta["manifest_version"], "performance-middlegames-v1")
            self.assertEqual(len(report["raw_measurements"]), 3+16*3)
            self.assertEqual(len(report["manifest_sha256"]), 64)
            for row in report["raw_measurements"]:
                self.assertGreater(row["elapsed_ms"], 0)
                if row["type"] == "search":
                    self.assertTrue(0 <= row["completed_depth"] <= 64)
                    self.assertGreater(row["nodes"], 0)
                    self.assertGreaterEqual(row["tt_hits"], 0)
            # Do not silently overwrite or publish failed runs.
            original = output.read_bytes()
            self.assertNotEqual(subprocess.run(cmd, capture_output=True).returncode, 0)
            self.assertEqual(output.read_bytes(), original)
            self.assertTrue(output.with_suffix(".md").exists())


if __name__ == "__main__":
    unittest.main()
