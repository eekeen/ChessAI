# Production evaluator and performance benchmarking

Production ChessAI uses **Hybrid V2**:

`Classic handcrafted evaluation + 0.25 * learned V2 residual correction`

The final score retains the existing ±1500 cp clipping and integer rounding.
`EvaluationConfig::ProductionHybridAlpha` in `PositionEvaluator.h` is the single
production-alpha constant. Normal startup, GameController/strongest AI search,
GUI startup and default tournaments inherit it. The GUI keeps Classic, ML and
Hybrid selectors and shows the model/Hybrid alpha beneath them. Classic remains
pure handcrafted evaluation; ML remains Direct V2. Tournament `--hybrid-alpha`
can explicitly override the default, including zero (exact, unclipped Classic).
No alpha was retuned and no weights were changed.

With both real V2 headers installed, the production model is
`v2-residual-3fb0a29e8514af8c`; Direct is `v2-direct-3b6bb568881c6bd0`.
V1 code/build support remains. Missing-model behavior is unchanged: legacy V1
can still supply its original blend, or Classic is used if no learned model is
available. The performance comparison requires **both V2 models** and refuses
to substitute V1.

## Build and exact measurement command

From the project root, on this Windows installation:

```powershell
$cmake = 'C:/Program Files (x86)/Microsoft Visual Studio/2019/Community/Common7/IDE/CommonExtensions/Microsoft/CMake/CMake/bin/cmake.exe'
& $cmake -S . -B build
& $cmake --build build --config Release
python benchmarks/benchmark_performance.py --repetitions 3 --evaluations 200000 --warmup 10000 --budgets 100,250,1000 --output benchmarks/performance_results.json
```

Use a new output filename for another run; the runner refuses to overwrite
existing measurements. JSON and companion Markdown are published only after a
successful complete native run, using atomic replacement for each file. Ctrl+C
terminates the child benchmark and does not publish an incomplete report.

The wrapper uses only Python's standard library. It launches
`build/Release/ChessAI_performance.exe`, which links the ordinary production
`ChessCore` (no diagnostic leaf hooks). The native tool accepts `--positions`,
`--repetitions`, `--evaluations`, `--warmup`, and comma-separated `--budgets`, and
emits metadata and raw measurement JSONL to stdout. Normal runs need no GUI.

## Position manifest and reproducibility

[performance-middlegames-v1.tsv](performance-middlegames-v1.tsv) is a separate
performance-only manifest. It contains 16 fixed middlegames, eight with each side
to move, with both queens and 20–28 pieces. It was selected from the existing
held-out split in `ml/data/lichess_250k_v2.npz` by a seeded permutation (`20260925`), filtering solely
on board composition and side counts, without evaluator/target scores. IDs
record the source dataset row. The source has four-field FENs, so clocks are
standardized to `0 1`. Legal moves and side-not-to-move king safety are checked
before timing. This selection and its clock convention do not make it a
strength test or a universal representation of chess positions.

The manifest is reused as-is; it is never regenerated based on timing results.
Frozen development, validation and final strength suites/results remain untouched.
JSON embeds every position, manifest SHA-256, executable SHA-256, native model
IDs, alpha, CPU/platform details, compiler/build type, available CMake flags,
time budgets, repetitions, warm-up settings, raw measurements and summaries.

## What is measured

**Static evaluation:** each mode is warmed up with 10,000 evaluations before
each measured batch. Each of three batches evaluates 200,000 positions, cycling
over the same 16 boards. This measures the production evaluation entry point:
feature extraction, network inference where applicable, Classic plus residual
for Hybrid, clipping and rounding. Position parsing/loading is excluded. A
consumed checksum prevents dead-code elimination. The batch clock is outside the
loop; average latency includes small loop/index/call overhead, without claiming
single-call latency percentiles. Latency standard deviation is across batches.
The evaluator order rotates per repetition to reduce consistent ordering bias.

**Search:** every position/mode has an excluded 10 ms search warm-up. Each of
100, 250 and 1000 ms is then measured on all 16 positions, three times per mode:
48 observations per budget/evaluator, 432 searches total. The mode order rotates
across positions, repetitions and budgets. Each evaluator uses the same timed
iterative deepening, max depth 64 and single search thread. Each has its own
262,144-entry transposition table, cleared before every sample outside timing.
There is no GUI difficulty weakening or opening book.

High-resolution wall time surrounds `findBestMoveTimed`; reported throughput
uses actual elapsed time, not the requested budget. The original integer engine
elapsed time is retained alongside it. Total nodes and TT hits include useful or
wasted work in an interrupted final iteration. **Completed depth** is the last
fully finished iteration, never the interrupted one; zero means fallback before
finishing depth one. A detected mate may stop search before its budget. Every
returned move is checked for legality outside the measured interval.

For each evaluator/budget, JSON includes total nodes, average/min/max/std nodes,
completed depth statistics, total elapsed time, weighted nodes/sec and TT hits.
The same statistics are grouped by position. Each individual repetition retains
nodes, depth, elapsed time, TT hits, best move and score. Static throughput is
total evaluations / total seconds; search throughput is total nodes / total
seconds, not an unweighted average of per-position rates.

## Results and interpretation

See [measured performance](performance_results.md) and
[full raw JSON](performance_results.json). These are measurements from this
machine/build, not a claim about other CPUs or about Stockfish playing strength.

The static comparison isolates the cost of invoking each evaluation path. Full
search also changes its tree when scores change: ordering, cutoffs, quiescence,
TT reuse within a search and early mates can differ. A depth difference is not
itself a strength conclusion. Neither nodes/sec nor nominal depth measures the
quality of the selected move.

No neural inference optimization was performed. If learned static evaluation is
the clear cost increase, profile that path next. These measurements alone do
not distinguish the cost of feature construction from dense network operations;
they do not justify attributing the bottleneck to one particular kernel.

Limitations: a small, deliberately repeatable suite; three timing repetitions;
warm caches for model weights/boards; ordinary OS scheduling; CPU affinity,
frequency, power and turbo settings are not controlled. Do not run training,
other benchmarks, or heavy workloads alongside the measured process. Short
budgets have proportionally greater scheduling/clock noise. No universal timing
or statistical strength claim follows from this report.

## Compatibility and regression checks

The old diagnostic executable and `eval_tool hybrid-v2` explicitly retain alpha
1.0 so their historical raw-residual analyses/parity semantics remain available.
`eval_tool hybrid-production` and the normal engine use the production constant.
The engine's read-only `hybridalpha` command exposes the active production value
to the GUI/protocol tests. `evalmode` selection remains unchanged.

Checks run for this change include CTest perft/evaluation/search/TT/game rules,
tournament scheduling/accounting and frozen suites; Python/C++ V2 features and
raw model parity plus production Hybrid parity; V1 parity in its baseline build;
protocol regression; actual Tk menu construction against the real engine;
tournament override/default tests; performance accounting/native smoke tests;
and the existing preprocessing and diagnostics tests. Short regression fixtures
are not strength-selection experiments. No new strength experiment was run.

Changed/created files:

| Area | Files |
|---|---|
| Production defaults/protocol | `src/engine/PositionEvaluator.h`, `src/engine/Search.h`, `src/game/GameController.h`, `src/main.cpp` |
| GUI | `src/gui/gui.py` |
| Tournament default/help | `src/benchmark/Tournament.h`, `src/benchmark/main.cpp` |
| Legacy diagnostic compatibility | `src/benchmark/Diagnostics.cpp`, `tests/eval_tool.cpp` |
| Performance implementation | `src/benchmark/Performance.cpp`, `benchmarks/benchmark_performance.py`, `CMakeLists.txt` |
| Performance inputs/output | `benchmarks/performance-middlegames-v1.tsv`, `benchmarks/performance_results.json`, `benchmarks/performance_results.md` |
| Regression checks | `tests/evaluation_tests.cpp`, `tests/opening_suite_tests.cpp`, `tests/tournament_smoke.py`, `tests/performance_tests.py`, `tests/gui_defaults_test.py`, `ml/test_protocol.py`, `ml/verify_v2.py` |
| Documentation | `README.md`, `benchmarks/PERFORMANCE.md` |

Tests cover production formulas, unchanged Classic/Direct,
alpha zero/overrides, completed-depth reporting, GUI defaults, report accounting
and output preservation. No frozen benchmark manifest or result was edited.

Exact additional checks (from the project root):

```powershell
python tests/performance_tests.py
python tests/gui_defaults_test.py
python tests/tournament_smoke.py
python tests/test_opening_manifests.py
python tests/diagnostic_tests.py
python ml/test_protocol.py --engine build/Release/ChessAI.exe
python -m unittest discover -s ml -p 'test_*.py'
python ml/verify_v2.py --direct ml/models/v2_huber/direct_best.pt --residual ml/models/v2_huber/residual_best.pt --data ml/data/lichess_250k_v2.npz
```

V1 inference parity uses the preserved `build-v1-baseline/Release/eval_tool.exe`
with `ml/verify_cpp.py --checkpoint ml/models/best.pt`; the normal V2 build does
not currently include V1 weights. Its absence there is not a V1 inference failure.
