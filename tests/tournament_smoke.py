"""CLI/report integration tests; short safety-capped games, NOT strength evidence."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile


def verify(executable):
    # List/validate only: never play held-out games in regression tests.
    for suite, version in [("development", "common-openings-v1"), ("heldout", "heldout-openings-v1")]:
        actual = subprocess.check_output([executable, "--opening-suite", suite, "--list-openings"], text=True)
        frozen = (Path(__file__).resolve().parents[1] / "benchmarks" / "suites" / (version + ".tsv")).read_text(encoding="utf-8")
        assert actual == frozen, "Frozen suite changed: " + suite
    with tempfile.TemporaryDirectory() as directory:
        reports = []
        for i, (first, second) in enumerate([("classic", "hybrid"), ("classic", "hybrid"),
                                             ("classic", "ml"), ("ml", "hybrid")]):
            output = Path(directory) / f"match{i}.json"
            command = [executable, "--white", first, "--black", second, "--games", "4",
                       "--depth", "1", "--max-plies", "10", "--seed", "42", "--output", str(output)]
            subprocess.run(command, check=True, capture_output=True, text=True, timeout=60)
            report = json.loads(output.read_text())
            assert report["complete"] and len(report["games"]) == 4
            assert report["config"]["opening_suite"] == "common-openings-v1"
            assert report["config"]["opening_suite_selection"] == "development"
            assert report["config"]["hybrid_alpha"] == .25
            summary = report["summary"]
            assert summary["games_completed"] == 4
            assert summary["white_wins"] + summary["black_wins"] + summary["draws"] == 4
            assert sum(s["points"] for s in summary["evaluators"].values()) == 4
            assert sum(s["score_percent"] for s in summary["evaluators"].values()) == 100
            assert sum(summary["termination_counts"].values()) == 4
            assert summary["termination_counts"]["max_ply_draw"] == 4
            assert summary["uncertainty"]["clusters"] == 2
            for evaluator in (first, second):
                for color in ("white", "black"):
                    games = [g for g in report["games"] if g[color] == evaluator]
                    wins = sum(g["result"] == ("1-0" if color == "white" else "0-1") for g in games)
                    draws = sum(g["result"] == "1/2-1/2" for g in games)
                    stats = summary["by_evaluator_color"][evaluator][color]
                    assert stats["games"] == len(games) == 2
                    assert stats["wins"] == wins and stats["draws"] == draws
                    assert stats["losses"] == len(games) - wins - draws
                    assert stats["score_percent"] == 100 * (wins + .5 * draws) / len(games)
            for index, game in enumerate(report["games"]):
                assert game["white"] == (second if index % 2 else first)
                assert game["black"] == (first if index % 2 else second)
                assert game["opening_index"] == report["games"][index - index % 2]["opening_index"]
                assert game["plies"] == len(game["moves"]) == 10
                assert game["moves"][:len(game["opening_moves"])] == game["opening_moves"]
                assert len(game["opening_fen"].split()) == 4
            reports.append(report)
        # Fixed depth + seed repeats games, excluding elapsed wall time.
        for a, b in zip(reports[0]["games"], reports[1]["games"]):
            for key in ["moves", "result", "termination", "opening_index", "white", "black", "nodes"]:
                assert a[key] == b[key], key
        for options in [["--games", "3"], ["--depth", "1", "--time-ms", "5"], ["--white", "invalid"], ["--opening-suite", "invalid"],
                        ["--hybrid-alpha", "nan"], ["--hybrid-alpha", "1.1"], ["--hybrid-alpha", "-0.1"], ["--hybrid-alpha", "0.5junk"]]:
            result = subprocess.run([executable, *options], capture_output=True, timeout=10)
            assert result.returncode != 0
        # Timed path also uses the same runner and evaluators.
        output = Path(directory) / "timed.json"
        subprocess.run([executable, "--games", "2", "--time-ms", "5", "--max-plies", "10",
                        "--output", str(output)], check=True, capture_output=True, timeout=60)
        report = json.loads(output.read_text())
        assert report["config"]["time_ms"] == 5 and report["config"]["fixed_depth"] == 0
        assert report["summary"]["uncertainty"]["score_first_ci95"] == [None, None]
        for alpha in (0, .1, .25, .5, .75, 1):
            output = Path(directory) / f"alpha{alpha}.json"
            subprocess.run([executable, "--games", "2", "--depth", "1", "--max-plies", "10",
                            "--hybrid-alpha", str(alpha), "--output", str(output)], check=True, capture_output=True, timeout=60)
            report = json.loads(output.read_text())
            assert abs(report["config"]["hybrid_alpha"] - alpha) < 1e-7
            if alpha == 0:
                assert report["games"][0]["moves"] == report["games"][1]["moves"]
                assert report["games"][0]["nodes"] == report["games"][1]["nodes"]
    print("CLI, all three evaluator pairings, JSON accounting, fixed-depth determinism and timed-mode smoke tests passed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", default="build/Release/ChessAI_tournament.exe")
    verify(parser.parse_args().engine)
