"""Profiling controls/accounting and bit-exact native decomposition checks."""
import json
from pathlib import Path
import subprocess
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
from profile_hybrid import summarize, STAGES


class HybridProfileTests(unittest.TestCase):
    def test_accounting_uses_production_denominator(self):
        rows = []
        for repeat in range(2):
            for stage in (*STAGES, "empty_control", "production_total", "linear1_no_skip_control"):
                us = 1 if stage == "empty_control" else 11 if stage == "production_total" else 3
                rows.append({"type": "measurement", "stage": stage, "position": 0, "repetition": repeat,
                             "iterations": 100, "elapsed_us": us*100})
        result = summarize(rows)["aggregate"]
        self.assertEqual(result["timings"]["classic"]["adjusted_us"], 2)
        self.assertEqual(result["timings"]["classic"]["percent_of_production_total"], 20)
        self.assertEqual(result["stage_sum_percent_of_production"], 180)
        self.assertEqual(result["unattributed_or_decomposition_gap_us"], -8)

    def test_native_parity_and_smoke(self):
        executable = "build-profile/Release/ChessAI_profile.exe"
        metadata = json.loads(subprocess.check_output([executable, "--verify-only"], text=True))
        self.assertEqual(metadata["alpha"], .25)
        self.assertEqual(metadata["model"], "v2-residual-3fb0a29e8514af8c")
        self.assertEqual(metadata["positions"], 16)
        self.assertGreater(metadata["parity_positions_including_children"], 600)
        raw = subprocess.run([executable, "--iterations", "20", "--warmup", "5", "--repetitions", "1"],
                             check=True, capture_output=True, text=True)
        rows = [json.loads(line) for line in raw.stdout.splitlines()]
        self.assertEqual(rows[-1]["type"], "complete")
        measurements = [r for r in rows if r["type"] == "measurement"]
        self.assertEqual(len(measurements), 16*20)
        self.assertTrue(all(r["elapsed_us"] > 0 for r in measurements))
        self.assertTrue(all(isinstance(r["elapsed_us"], float) for r in measurements))
        self.assertTrue(all(r["requested_iterations"] == 20 and r["iterations"] >= 20 for r in measurements))
        self.assertTrue(all(r["elapsed_us"] >= rows[0]["minimum_batch_us"] for r in measurements))
        controls = [r for r in measurements if r["stage"] == "empty_control"]
        self.assertEqual(len(controls), 16)
        self.assertTrue(all(r["elapsed_us"] / r["iterations"] > 0 for r in controls))

    def test_candidate_comparison_smoke(self):
        result = subprocess.run(["build-profile/Release/ChessAI_profile.exe", "--compare-candidates",
                                 "--iterations", "20", "--warmup", "5", "--repetitions", "1"],
                                check=True, capture_output=True, text=True)
        rows = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(rows[-1]["type"], "complete")
        measurements = [r for r in rows if r["type"] == "measurement"]
        self.assertEqual(len(measurements), 16*15)
        stages = {r["stage"] for r in measurements}
        self.assertTrue({"reference_total", "tail_total", "sparse_total", "active_total",
                         "sparse_only_total", "active_only_total", "list_construction_control"} <= stages)
        self.assertTrue(all(r["elapsed_us"] >= rows[0]["minimum_batch_us"] for r in measurements))


if __name__ == "__main__":
    unittest.main()
