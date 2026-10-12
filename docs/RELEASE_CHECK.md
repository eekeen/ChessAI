# v1.0.0 release checks

The detailed measurements below are the earlier release-preparation record.
See the [final pre-ship audit](PUBLICATION_AUDIT.md) for the latest checks and
publication blockers. Historical full-corpus measurements were not rewritten.

Release preparation was checked on Windows with MSVC 19.28 (Visual Studio 2019), Python 3.11 and Ryzen 7 3700X. The source/model/alpha configuration is unchanged. No frozen final internal or Stockfish strength matches were rerun.

## Build and regressions

From the repository root, with CMake available in a Visual Studio developer shell:

```powershell
cmake -S . -B build -A x64
cmake --build build --config Release --parallel 4
Push-Location build
ctest -C Release --output-on-failure
Pop-Location
python -m pip install -r ml/requirements.txt
python -m pip install -r benchmarks/elo/requirements.txt
python -m pip install Pillow
python tests/tournament_smoke.py
python tests/test_opening_manifests.py
python tests/diagnostic_tests.py
python tests/performance_tests.py
python tests/gui_defaults_test.py
python ml/test_protocol.py --engine build/Release/ChessAI.exe
python -m unittest discover -s ml -p 'test_*.py'
python tests/calibration_tests.py
python ml/verify_cpp.py --tool build/Release/eval_tool.exe
cmake -S . -B build-profile -A x64 -DCHESSAI_BUILD_PROFILER=ON
cmake --build build-profile --config Release --parallel 4
python tests/hybrid_profile_tests.py
```

Both Release builds passed. All four CTest groups passed: perft, evaluation/search/game rules, tournament and opening suites. Python tournament, manifests, diagnostics, performance, actual Tk defaults, protocol, preprocessing, calibration and profiler regressions passed. Calibration tests use a fake UCI opponent and native adapter; they do not run the frozen Stockfish match. The full GUI was also constructed with real assets and its event loop exercised successfully before closing it.

`tests/calibration_fixture_smoke.py` is a create-once artifact publisher, not a repeatable test runner. It was not rerun because doing so targets preserved fixture artifacts. Its integration behavior is covered by `calibration_tests.py`.

## Full-corpus parity (local research artifacts required)

These commands require the original local dataset/checkpoints, intentionally excluded from the public source checkout. Select a new output filename if it already exists:

```powershell
python ml/verify_v2.py --tool build/Release/eval_tool.exe --direct ml/models/v2_huber/direct_best.pt --residual ml/models/v2_huber/residual_best.pt --data ml/data/lichess_250k_v2.npz
python tests/verify_optimized_v2.py --tool build/Release/eval_tool.exe --require-avx2 --output build/release-parity.json
```

Release verification passed: 264 positions with exact 789-feature parity; raw Python/C++ differences at most 0.001342 cp direct and 0.001464 cp residual, within the existing 0.02 cp tolerance. Stored V2 features and residual targets also passed. All 250,000 positions matched the C++ reference bit-for-bit across tested backends, with zero rounded Hybrid changes.

The legacy V1 prediction check requires a V1-enabled build. Production V2 intentionally has no `MLWeights.h`; asking its tool for V1 predictions returns unavailable. Do not install legacy weights into production to make that optional check run. V1 feature checks remain available in the production tool. The existing isolated `build-v1-baseline` also passed V1 prediction parity against its original checkpoint (maximum 0.498413 cp including rounding). Historical V1 material sanity failures remain unchanged and are not production V2 regressions.

## Behavior and artifact preservation

Before/after fixed-depth outputs matched for 48 cases (16 positions, three evaluators, depth 3), including scores, moves and node counts. SHA-256 checks found no changes to 197 protected source/test/workflow/benchmark files, including CMake and production weights. Runtime GUI checks confirmed `v2-residual-3fb0a29e8514af8c`, Hybrid alpha 0.25 and all three evaluator modes. Release logs and parity evidence are local in ignored `build/release-check/`.

The version exists only in `VERSION` and documentation. No search behavior, move generation, evaluation behavior, kernels, model weights, time management or strength settings changed.
