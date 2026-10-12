# Frozen evaluator diagnostics

**Current protocol:** alpha 0.25 is frozen after validation. Earlier alpha pilots
below are historical, not instructions for further tuning. Use the
[FINAL suite](FINAL.md) for the two authorized final experiments.

This workflow measures existing models without training or changing weights.
Run from the repository root with NumPy installed and both real V2 weight headers.

## Build and run

```powershell
$cmake = 'C:/Program Files (x86)/Microsoft Visual Studio/2019/Community/Common7/IDE/CommonExtensions/Microsoft/CMake/CMake/bin/cmake.exe'
& $cmake -S . -B build
& $cmake --build build --config Release
python benchmarks/diagnose_evaluators.py --data ml/data/lichess_250k_v2.npz --parents 500 --leaf-roots 6 --leaf-samples 1000 --seed 42 --output benchmarks/diagnostic_report.json
```

Outputs: `diagnostic_report.json`, `diagnostic_report.md`, and
`diagnostic_report.samples.jsonl`. Each file is replaced atomically after
calculations succeed. Use a new prefix to preserve an earlier experiment.
JSONL retains parents, every legal child/move/target, and sampled leaf FENs/scores.
JSON includes model IDs, dataset/executable hashes, parent indices, search
summaries, all thresholds/percentiles, and existing `*_depth3_32.json` match
summaries. No Lichess dump scan is needed.

The report separates global test MAE/RMSE, sibling ranking, parent-child
stability, residual corrections, clipping and actual search-leaf distributions.
Raw global MAE reproduces the earlier training report; deployed MAE also includes
clipping and rounding. The measured quiet-move changes and correction magnitudes
are observations, not proof of why the neural models lose games.

## Trusted child labels

Without Stockfish, targets come only from the supplied NPZ. Matching uses the
first four FEN fields, retains en-passant, ignores clocks/history, and excludes
conflicting labels. Coverage is conservative. Only complete labelled sets with
at least two legal moves contribute to ranking. No child labels are fabricated.
The real 500-parent local run has no usable complete multi-move sets.

To use an installed Stockfish executable:

```powershell
python benchmarks/diagnose_evaluators.py --stockfish 'C:/path/to/stockfish.exe' --stockfish-depth 12 --parents 500 --leaf-roots 6 --seed 42 --output benchmarks/diagnostic_stockfish.json
```

This labels **every** child with that engine/depth: one thread, 64 MB hash,
MultiPV 1, full strength, fresh hash per child. Old Lichess labels are not mixed
with newly searched scores. Repeated identical six-field FENs reuse scores within
the run. Engine ID/hash/settings and labels are retained; a per-search timeout
prevents indefinite waiting. Nothing is downloaded automatically.

UCI scores are converted from child-side perspective to White cp. Rankings
maximize for a White parent and minimize for Black. Mate-containing sets are
counted separately and excluded from cp ranking/regret; mate scores are never
converted to arbitrary cp. Forced moves do not test ranking. Target search
depth, Stockfish version and score normalization limit interpretation.
The integration follows Stockfish's [developer guidance](https://official-stockfish.github.io/docs/stockfish-wiki/Developers.html);
its [score interpretation](https://official-stockfish.github.io/docs/stockfish-wiki/Stockfish-FAQ.html)
also explains why cp scales should not be assumed identical across source versions.

Top-1 accepts any target-best tie. Top-3 means a target-best move appears among
the evaluator's first three. Prediction ties break by UCI lexicographic order;
uniform tie expectations are also reported. Pairwise ignores target ties,
credits predicted ties by 0.5, and averages parents equally. Spearman uses average
ranks and excludes constant vectors. Regret is target-best minus target-selected
from the parent perspective. Missing metrics are null, not zero.

## Raw scores and search leaves

`direct_raw`, `residual_raw` and `hybrid_raw = Classic + residual_raw` are
unclipped diagnostic floats. `ml` and `hybrid` are deployed clipped/rounded
integers. Clip-induced sibling ties compare raw versus clipped floats, excluding
rounding, at exact and 5 cp tolerances. Boundary-label counts cannot recover
original unbounded targets.

`ChessAI_diagnostics.exe` reads six-field FEN lines from stdin and writes JSONL.
Options: `--children --leaf-roots 6 --leaf-samples 1000 --depth 3 --seed 42`.
The Python runner fixes search depth at three. Each mode/root starts with a fresh
TT and identical settings. Reservoirs uniformly sample static evaluation events,
including quiescence stand-pat. Repeated positions remain eligible and expensive
roots contribute more events. Quiescence can produce plies beyond three.
Terminal mate scores are not static evaluation events. Incoming move type
includes en-passant; -1 means root/unknown.

Instrumentation is compiled only into `ChessCoreDiagnostics`. Production engine
and tournament builds have no leaf observer calls or runtime logging branch.
Regression tests compare instrumented and production moves, scores and node counts.

## Hybrid alpha pilots

The original 16-opening suite is now development data and must not be used again
to choose final alpha. The commands below are retained as historical development
instructions. Use the [frozen held-out validation protocol](HELDOUT.md) for the
preregistered 0.10 and 0.25 candidates; do not tune new values on that set.

`--hybrid-alpha` accepts finite values in [0,1], default **1.0**. For positive
alpha the score remains `round(clamp(Classic + alpha * residual, -1500, 1500))`.
Alpha **0** exactly equals Classic, including outside the clipping range.
Alpha **1** preserves current Hybrid. Changing alpha invalidates the TT.
This is a V2 tournament experiment; GUI/training defaults are unchanged.

These commands are provided, **not run** as part of the report. Each pilot uses
32 games, depth three, the same seed and the same 16 paired openings:

```powershell
foreach ($alpha in @('0.10', '0.25', '0.50', '0.75', '1.00')) {
    & ./build/Release/ChessAI_tournament.exe --white classic --black hybrid --hybrid-alpha $alpha --games 32 --depth 3 --max-plies 300 --seed 42 --output "benchmarks/classic_vs_hybrid_alpha_${alpha}_pilot.json"
    if ($LASTEXITCODE -ne 0) { throw "Pilot failed for alpha $alpha" }
}
```

Keep max-ply draws and opening-cluster confidence intervals in the reports.
Do not select a final alpha solely on these openings; validate with new held-out
openings and search budgets.

## Verification

```powershell
Push-Location build
& 'C:/Program Files (x86)/Microsoft Visual Studio/2019/Community/Common7/IDE/CommonExtensions/Microsoft/CMake/CMake/bin/ctest.exe' -C Release --output-on-failure
Pop-Location
python tests/diagnostic_tests.py
python tests/tournament_smoke.py
python -m unittest discover -s ml -p 'test_*.py'
python ml/test_protocol.py --engine build/Release/ChessAI.exe
```

Tests cover ranking perspective/ties/regret, clipping attribution, residual
buckets, UCI parsing, seeded leaf sampling, captures/promotions, production search
parity, report generation, alpha endpoints/intermediate values and TT invalidation.
