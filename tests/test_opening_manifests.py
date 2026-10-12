"""Frozen opening manifests only: no searches, evaluator scores, or matches."""
import hashlib
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
FROZEN = {
    "development": ("common-openings-v1", "045c3674e35e12915487e7d081d405ed769f1c6de8d881f3411946333e9cafee", 16),
    "heldout": ("heldout-openings-v1", "77236baca02e42a32ee53ee3f60e385f3e764a62ed1c54c0114c88f5cbea9a82", 32),
    "final": ("final-openings-v1", "3f5e12a70b053741d4c8b8664684f384c52d60d79dc7331f0b9c3c2b5a2445c7", 64),
}


class OpeningManifestTests(unittest.TestCase):
    def test_frozen_manifests(self):
        for suite, (version, digest, count) in FROZEN.items():
            with self.subTest(suite=suite):
                text = (ROOT / "benchmarks/suites" / (version + ".tsv")).read_text(encoding="utf-8")
                self.assertEqual(hashlib.sha256(text.encode("utf-8")).hexdigest(), digest,
                                 "Frozen suite changed; never regenerate from results")
                actual = subprocess.check_output([str(ROOT / "build/Release/ChessAI_tournament.exe"),
                                                  "--opening-suite", suite, "--list-openings"], text=True)
                self.assertEqual(actual, text)
                self.assertEqual(len(text.splitlines()) - 1, count)
                self.assertEqual(text.splitlines()[0], version)

    def test_native_overlap_and_pairing(self):
        subprocess.run([str(ROOT / "build/Release/opening_suite_tests.exe")], check=True, capture_output=True)


if __name__ == "__main__":
    unittest.main()
