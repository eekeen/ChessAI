import argparse
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import subprocess
import sys
import zstandard

import numpy as np
from features import features_from_fen, START_FEN
from make_example import write_example, example_records
from preprocess_dataset import extract_record, preprocess


class PipelineTests(unittest.TestCase):
    def test_features(self):
        x = features_from_fen(START_FEN)
        self.assertEqual(int(x[:768].sum()), 32)
        self.assertEqual(x[3 * 64], 1)  # White rook a1
        self.assertEqual(x[10 * 64 + 59], 1)  # Black queen d8
        np.testing.assert_array_equal(x[768:], [1, 1, 1, 1, 1])
        self.assertEqual(features_from_fen(START_FEN.replace(" w ", " b "))[768], -1)
        for fen in ["bad", START_FEN.replace("RNBQKBNR", "RNBQXBNR"), START_FEN.replace("KQkq", "KK")]:
            with self.assertRaises(ValueError):
                features_from_fen(fen)

    def test_labels(self):
        record = {"fen": START_FEN.replace(" w ", " b "), "evals": [
            {"depth": 10, "pvs": [{"cp": 20}]},
            {"depth": 20, "knodes": 5, "pvs": [{"cp": 300}, {"cp": -1000}]},
            {"depth": 21, "pvs": [{"cp": "bad"}, {"cp": 999}]}, None]}
        self.assertEqual(extract_record(record)[1], 300)
        self.assertEqual(extract_record(record, "stm")[1], -300)
        record["evals"].append({"depth": 30, "pvs": [{"mate": -3}]})
        self.assertEqual(extract_record(record)[1], -1500)
        record["evals"][-1]["pvs"][0] = {"mate": 0}
        self.assertEqual(extract_record(record)[1], 1500)
        record["evals"][-1]["pvs"][0] = {"cp": 30000}
        self.assertEqual(extract_record(record)[1], 1500)
        record["evals"] = [{"pvs": [{"cp": float("nan")}]}]
        with self.assertRaises(ValueError):
            extract_record(record)

    def test_stream_reservoir_splits(self):
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            source = str(Path(directory) / "example.zst")
            write_example(source)
            outputs = []
            for i in range(2):
                target = str(Path(directory) / f"data{i}.npz")
                stats = preprocess(argparse.Namespace(input=source, output=target, samples=350,
                    seed=42, max_records=None, dedup_dir=None, score_perspective="white"))
                with np.load(target) as data:
                    outputs.append({key: data[key].copy() for key in ["X", "y", "split", "fen"]})
                self.assertEqual(stats["stats"]["duplicates"], 10)
                self.assertEqual(stats["stats"]["malformed_records"], 3)
                self.assertEqual(stats["sampled_bins"], [50] * 7)
                self.assertEqual(stats["split_counts"], [280, 35, 35])
            for key in outputs[0]:
                np.testing.assert_array_equal(outputs[0][key], outputs[1][key])
            self.assertEqual(len(set(outputs[0]["fen"])), 350)

    def test_bounded_cli_and_redistribution(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "skewed.zst"
            records = list(example_records(9000))
            # One rare bin, five absent bins, and a dominant equal-position bin.
            for i, record in enumerate(records):
                record["evals"][-1]["pvs"][0]["cp"] = -1200 if i < 3 else 0
            lines = [json.dumps(r) for r in records]
            lines[10] = "{bad"
            lines[11] = lines[0]
            source.write_bytes(zstandard.ZstdCompressor().compress("\n".join(lines).encode()))
            outputs = []
            for i, extra in enumerate((["--max-records", "8000"], [])):
                target = Path(directory) / f"bounded{i}.npz"
                result = subprocess.run([sys.executable, str(Path(__file__).with_name("preprocess_dataset.py")),
                    "--input", str(source), "--output", str(target), "--samples", "1000", "--seed", "42", *extra],
                    capture_output=True, text=True, check=True, timeout=30)
                self.assertIn("Read: 8,000 / 8,000", result.stdout)
                self.assertIn("Final selected samples: 1,000", result.stdout)
                with np.load(target) as data:
                    metadata = json.loads(str(data["metadata"]))
                    self.assertEqual(data["X"].shape, (1000, 773))
                    self.assertEqual(len(set(data["fen"])), 1000)
                    outputs.append({key: data[key].copy() for key in ["X", "y", "split", "fen"]})
                self.assertEqual(metadata["max_records"], 8000)
                self.assertEqual(metadata["stats"], dict(positions_read=8000, positions_accepted=7998,
                                                       malformed_records=1, duplicates=1))
                self.assertEqual(metadata["sampled_bins"], [3, 0, 0, 997, 0, 0, 0])
                self.assertEqual(metadata["redistributed_samples"], 854)
                self.assertEqual(sum(metadata["split_counts"]), 1000)
            for key in outputs[0]:
                np.testing.assert_array_equal(outputs[0][key], outputs[1][key])

    def test_short_input(self):
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            source = str(Path(directory) / "example.zst")
            write_example(source, 35)
            stats = preprocess(argparse.Namespace(input=source, output=str(Path(directory) / "data.npz"),
                samples=1000, seed=42, max_records=8000, dedup_dir=None, score_perspective="white"))
            self.assertEqual(stats["selected"], 35)
            self.assertEqual(stats["stats"]["positions_read"], 48)

    def test_interrupt_preserves_outputs(self):
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            source = str(Path(directory) / "example.zst")
            write_example(source, 70)
            target = Path(directory) / "data.npz"
            args = argparse.Namespace(input=source, output=str(target), samples=35, seed=42,
                                      max_records=None, dedup_dir=directory, score_perspective="white")
            preprocess(args)
            original = target.read_bytes()
            sidecar = target.with_suffix(".metadata.json")
            original_metadata = sidecar.read_bytes()
            def interrupt_write(file, **arrays):
                file.write(b"incomplete ZIP")
                raise KeyboardInterrupt
            for exists in (True, False):
                if not exists:
                    target.unlink()
                    sidecar.unlink()
                for stage, effect in [("preprocess_dataset.extract_record", KeyboardInterrupt),
                                      ("preprocess_dataset.np.savez_compressed", interrupt_write)]:
                    with patch(stage, side_effect=effect), self.assertRaises(KeyboardInterrupt):
                        preprocess(args)
                    if exists:
                        self.assertEqual(target.read_bytes(), original)
                        self.assertEqual(sidecar.read_bytes(), original_metadata)
                    else:
                        self.assertFalse(target.exists())
                        self.assertFalse(sidecar.exists())
                    self.assertFalse(list(Path(directory).glob(".*.tmp")))
                    self.assertFalse([p for p in Path(directory).iterdir() if p.is_dir()])


if __name__ == "__main__":
    unittest.main()
