"""Regression check for existing protocol and evaluator selection."""
import argparse
import subprocess


def verify(engine):
    process = subprocess.Popen([engine], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, text=True)
    def command(text):
        process.stdin.write(text + "\n")
        process.stdin.flush()
        return process.stdout.readline().strip()
    try:
        assert process.stdout.readline().strip() == "ready"
        assert command("ping") == "pong"
        available = command("model") != "model unavailable"
        modes = command("evalmodes").split()[1:]
        default = "hybrid" if "hybrid" in modes else "classic"
        assert command("evalmode") == f"evalmode {default}"
        assert command("hybridalpha") == "hybridalpha 0.25"
        current = default
        for mode in ["ml", "hybrid", "classic"]:
            response = command(f"evalmode {mode}")
            assert response == ("ok" if mode in modes else "error model_unavailable")
            if mode in modes:
                current = mode
            assert command("evalmode") == f"evalmode {current}"
        assert command("evalmode nonsense") == "error invalid_evalmode"
        assert command("evalmode ml extra") == "error invalid_evalmode"
        assert command("evalmode") == "evalmode classic"
        assert command("evaluate").startswith("evaluation classic 0 ml ")
        assert command("move e2e5") == "illegal"
        assert command("move e2e4") == "ok capture 0"
        assert command("turn") == "turn black"
        assert command("state") == "state ongoing"
        assert command("newgame") == "ok"
        assert command("turn") == "turn white"
        assert command("go 50 2 2000").startswith("bestmove ")
        assert command("turn") == "turn black"
        assert command("quit") == "bye"
        assert process.wait(timeout=10) == 0
        print(f"Protocol regression passed; model available={available}")
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
        process.stdin.close()
        process.stdout.close()
        process.stderr.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", required=True)
    verify(parser.parse_args().engine)
