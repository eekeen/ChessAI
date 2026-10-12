# ChessAI learned position evaluator

**V2 is now available:** see [the V2 guide](README_V2.md) for explicit material
features, exact C++ Classic targets, dedicated residual learning and matched
experiments on the existing 250k positions. This page documents the retained V1
pipeline and its original smoke validation.

This pipeline trains a 773 -> 128 -> 64 -> 1 ReLU MLP from existing Stockfish
labels. It does not run Stockfish or generate training labels. Alpha-beta,
quiescence, iterative deepening, move generation and game rules remain C++.
This page describes the original V1 experiment. The public production checkout
includes V2 weights and defaults to residual Hybrid at alpha 0.25; see
[the current deployment guide](../docs/ML_EVALUATION.md).

## Requirements and data source

Python 3.11+ for preprocessing/training/export/tests. Install:

```powershell
python -m pip install -r ml/requirements.txt
```

Required packages: numpy, zstandard, torch, matplotlib. Tested here with
numpy 2.4.6, zstandard 0.25.0, torch 2.9.1+cpu, matplotlib 3.10.9.
No seaborn, python-chess, Stockfish binary, ONNX or runtime ML library is needed.
For CUDA, install the appropriate PyTorch build using its official installation
instructions. `--device auto` selects CUDA when available, otherwise CPU.
Tkinter remains the existing GUI frontend; the **engine executable** requires no Python.

Download the **evaluations** JSONL/Zstandard file from
[Lichess open database](https://database.lichess.org/#evals), not the PGN game dump
or puzzle CSV. Lichess publishes these exports under CC0. Put it at:

```text
ml/data/lichess_db_eval.jsonl.zst
```

The official schema has four-field `fen` and an `evals` array containing
`depth`, `knodes`, and `pvs` (each primary variation has `cp` or `mate`).
The parser selects the highest-depth usable **first PV**, with node count as
tie-breaker, as recommended by Lichess. It never substitutes a weaker move's PV
for an unusable primary PV. Unknown fields are ignored; unusable records are counted.
The official scores are White-relative: **do not negate them for Black to move**.
Lichess's [UCI score conversion](https://github.com/lichess-org/lila/blob/master/ui/lib/src/ceval/protocol.ts)
already changes the sign on Black's turn before storing the evaluation.
`--score-perspective stm` is provided only for other inputs with side-to-move scores.
Scores are clipped to +/-1500 cp; signed mates map to the matching extreme.
Mate zero means the side to move is mated.

## Preprocess

Run all commands from the repository root unless indicated otherwise:

```powershell
python ml/preprocess_dataset.py --input ml/data/lichess_db_eval.jsonl.zst --output ml/data/lichess_250k.npz --samples 250000 --seed 42
```

Zstandard is decompressed as a stream, never as a complete disk file. Seven
independent uniform reservoirs have nearly equal quotas over bins
`[-inf,-800), [-800,-300), [-300,-100), [-100,100), [100,300), [300,800), [800,inf)`.
The default scans at most `max(samples * 8, samples)` **raw records**, including
malformed records and duplicates: 2,000,000 records for 250,000 requested samples.
It stops at that limit or EOF, whichever comes first, then writes the dataset.
Override the limit with a positive `--max-records N`; zero is no longer an
unlimited-scan option. No full-file scan is required. For example:

```powershell
python ml/make_example.py --output ml/data/capped_example.jsonl.zst --count 9000
python ml/preprocess_dataset.py --input ml/data/capped_example.jsonl.zst --output ml/data/example_1k.npz --samples 1000 --max-records 8000 --seed 42
```

The original seven stratified reservoirs are preserved. A separate uniform
overflow reservoir holds up to `samples` rejected/evicted primary samples. At
completion, unused bin capacity is filled from this reserve, without duplicates
or a second pass. Additional samples follow the available surplus distribution;
rare bins are retained, but the final bins need not be equal. Output contains
exactly `samples` positions whenever the scanned prefix has at least that many
unique usable positions. Otherwise all available positions are saved (at least
10 are required for the three splits). Sampling and splitting remain deterministic
for the same input, limit and seed.

Progress shows records read versus the cap, unique usable positions, primary
reservoir size versus requested samples, per-bin counts and overflow reserve size.
The final summary reports raw/usable/selected counts, bin counts, duplicates,
malformed records, evaluation min/max/mean/std and train/validation/test sizes.
The bounded prefix can differ from the full dump's distribution; report the scan
limit with model metrics.

Output is staged in temporary files in the destination directory. Ctrl+C during
scanning or serialization cleans up temporary files and preserves existing output.
Only fully written files are published using atomic replacements. The NPZ embeds
the authoritative metadata; if interrupted between the NPZ and JSON sidecar
replacements, the NPZ is complete but the optional sidecar may be stale or absent.

An exact SQLite index on disk deduplicates positions with bounded cache memory
(32 MiB). Its storage grows with corpus size, so allow ample temporary disk space;
use `--dedup-dir D:/scratch` to select an existing scratch directory. Reservoir RAM
is O(samples) (up to two times the requested count across both reservoirs); the
SQLite index grows only with the scanned prefix and is removed after processing,
including on failure.
FEN counters and en passant are excluded from the dedup key because v1 cannot see
them; this is stricter than exact FEN deduplication. The first usable record for a
key wins, while the deepest evaluation **within that record** supplies the target.
The FEN parser checks standard-chess syntax and king counts, not full reachability.

The compressed NPZ contains `X` (int8 N x 773), `y` (float32 White cp), `split`
(0=train, 1=validation, 2=test), `fen`, selected `depth`, and JSON `metadata`.
Splits are seeded and stratified approximately 80/10/10, without duplicate inputs.
Small-bin rounding can shift the proportions. Metadata also saves source path,
size/mtime, arguments, bin boundaries, counts and score statistics. A sibling
`.metadata.json` is human-readable. Training records the NPZ SHA256.

This is a **stratified prefix benchmark with capacity redistribution**, not the
natural frequency of Lichess positions. Similar positions from related games may remain across splits because
the evaluation dump does not supply game identifiers. Report this limitation
alongside metrics; do not describe the test split as game-independent.

## Exact feature contract (version 1)

Plane order: `P N B R Q K p n b r q k` (White first). Each plane has 64 binary
features, indexed `plane * 64 + square`. Squares are a1=0, b1=1, ..., h8=63.
Index 768 is +1 for White to move, -1 for Black. Indices 769..772 are binary
White kingside, White queenside, Black kingside, Black queenside castling rights.
No board rotation, side-relative piece ordering, en passant or counters.
Python uses `features.features_from_fen`; C++ uses `MLEvaluation::features`.

## Train and report

```powershell
python ml/train_evaluator.py --data ml/data/lichess_250k.npz --epochs 100 --batch-size 512 --learning-rate 0.001 --device auto --output-dir ml/models
```

Targets are cp/1000. AdamW minimizes mean squared error. Every epoch prints
training MSE and validation MSE/MAE/RMSE. Seeds control Python/NumPy/PyTorch,
deterministic algorithms are enabled, and the data loader uses a seeded generator.
Results may still differ between hardware/software versions. `--threads 4`,
`--seed 42`, and `--patience 10` are configurable.

`best.pt` is selected **only by validation MSE**, with early stopping after
`patience` epochs without improvement. The best checkpoint is reloaded before a
single test evaluation. `metrics.json` contains best epoch, training history,
validation/test errors in cp, test errors by absolute-score range, raw and clipped
test predictions' metrics, versions, and dataset hash. Plots:
`prediction_vs_target.png` and `error_distribution.png`.

Sanity checks report a start score within +/-150 cp and shifts of at least 300 cp
in the expected direction when either queen is removed. These thresholds are
explicit heuristics, not evidence of playing strength. Inspect failed checks
before deploying; the pipeline does not quietly declare a failed model good.

## Export, build and verify

These historical V1 commands require locally prepared data and checkpoints,
which are excluded from publication. Use a separate research checkout/build for
exports; they are not production setup instructions. Recorded metrics remain
available at [metrics.json](models/metrics.json).

```powershell
python ml/export_model.py --checkpoint ml/models/best.pt --output src/engine/generated/MLWeights.h
cmake -S . -B build
cmake --build build --config Release --clean-first
Push-Location build
ctest -C Release --output-on-failure
Pop-Location
python ml/test_pipeline.py
python ml/test_protocol.py --engine build/Release/ChessAI.exe
python ml/verify_cpp.py --tool build/Release/eval_tool.exe --checkpoint ml/models/best.pt --require-sanity
```

Use a clean rebuild when adding/removing the optional header: an earlier compiler
dependency list may not know that a previously absent `__has_include` target exists.
The generated header contains float32 arrays, sizes, feature/model versions,
target scale, clip bound and a checkpoint hash in the model identifier. Layer 1
is exported input-major; layers 2 and 3 use PyTorch's output-major layout.

Use a Visual Studio developer shell with CMake on PATH. For a fresh Windows
build directory use `cmake -S . -B build -A x64`. On Unix use the
appropriate CMake generator and `build/eval_tool` (no `.exe` or `Release/`).

C++ inference uses stack arrays and sparse first-layer additions followed by
two dense layers and ReLUs. No per-evaluation heap allocations, Python interpreter
or model file loading. Integer results use nearest rounding and +/-1500 clipping,
far below search's +/-100000 mate scores. Search/game logic still owns mates.

## Modes, GUI and speed

Run `build/Release/ChessAI.exe`; the existing one-line stdin/stdout protocol adds:

```text
evalmode                 -> evalmode classic (or ml/hybrid)
evalmode classic         -> ok
evalmode ml              -> ok, or error model_unavailable
evalmode hybrid          -> ok, or error model_unavailable
evaluate                 -> evaluation classic 0 ml unavailable hybrid unavailable
model                    -> model unavailable (or version/hash identifier)
```

With a model, `evaluate` reports all three numeric White cp scores for the current
game position. Unknown modes return `error invalid_evalmode`. Unavailable modes
do not change the active mode. Mode changes clear the transposition table; new
games preserve the selection. All search evaluation calls go through
`PositionEvaluator`; the original `Evaluation` implementation is unchanged.

Hybrid uses 25% ML + 75% Classic, configurable in the single
`EvaluationConfig::HybridMLWeight` constant in `PositionEvaluator.h`. This is an
experimental conservative prior retaining the existing material signal, **not a
tuned or measured optimum**. Default is Hybrid when a generated model is compiled
in, Classic otherwise. Programmatic missing-model evaluation falls back to Classic;
protocol/UI explicitly mark ML as unavailable instead of reporting fake ML scores.

```powershell
python src/gui/gui.py
build/Release/eval_tool.exe bench 100000
```

The GUI retains its layout and adds a small evaluator selector, disabling ML and
Hybrid without weights. It prefers Release over Debug so a stale Debug executable
does not hide newly built functionality. GUI difficulty ratings remain uncalibrated
targets, not verified Elo. Benchmark output gives model ID, five FENs with all
available scores, evaluations/second and a checksum. Use Release builds. These are
microbenchmarks, not search NPS or Elo; measure actual playing strength separately.

## Reproducible synthetic smoke test

No real dataset was found in this repository. The following validates the full
software path with intentionally arbitrary labels; **it does not train useful chess**:

```powershell
python ml/make_example.py
python ml/preprocess_dataset.py --input ml/data/example.jsonl.zst --output ml/data/smoke.npz --samples 350 --seed 42
python ml/train_evaluator.py --data ml/data/smoke.npz --output-dir ml/models/smoke --epochs 3 --batch-size 64 --device cpu --synthetic
python ml/export_model.py --checkpoint ml/models/smoke/best.pt --output ml/models/smoke/MLWeights.h --allow-synthetic
$modelHeader = (Resolve-Path ml/models/smoke/MLWeights.h).Path.Replace('\','/')
cmake -S . -B build-ml-smoke -G "Visual Studio 16 2019" -A x64 "-DCHESSAI_ML_WEIGHTS_HEADER=$modelHeader"
cmake --build build-ml-smoke --config Release
Push-Location build-ml-smoke
ctest -C Release --output-on-failure
Pop-Location
python ml/verify_cpp.py --tool build-ml-smoke/Release/eval_tool.exe --checkpoint ml/models/smoke/best.pt
python ml/test_protocol.py --engine build-ml-smoke/Release/ChessAI.exe
build-ml-smoke/Release/eval_tool.exe bench 100000
```

Synthetic export requires an explicit flag; this workflow does not place weights
in `src/engine/generated` or change the normal executable. `--require-sanity` is
intentionally absent here because arbitrary labels fail chess sanity checks.

Verified during implementation (CPU/MSVC Release):

- 713 input lines: 700 unique accepted, 10 duplicates, 3 malformed; 350 selected,
  50 per bin, splits 280/35/35. Deterministic replay passed.
- Starting-position perft depths 1..5: 20, 400, 8902, 197281, 4865609.
- Kiwipete depths 1..4: 48, 2039, 97862, 4085603.
- CTest passed in both missing-model and model-present builds: legal search,
  checkmate/stalemate, TT clearing on mode change, repetition and hashing checks.
- Exact feature agreement for 237 positions (both turns, all 16 castling masks,
  missing queens, en passant and varied pieces); prediction maximum difference
  0.497652 cp, including C++ integer rounding.
- Protocol regression passed in both builds. Hidden Tkinter construction verified
  Classic default, disabled unavailable modes, menu fit and transition into play.
- Synthetic epoch-3 train MSE 0.446784; validation MSE 0.484639,
  MAE 548.56 cp, RMSE 696.16 cp; test MAE 542.91 cp, RMSE 700.61 cp.
  These are **software smoke metrics only**, not Lichess model performance.
- Synthetic model benchmark: approximately 2.39M Classic, 112k ML, 109k Hybrid
  evaluations/second on this machine. Timing depends on hardware/load/compiler.

Remaining work: obtain the real dump, train, review held-out metrics and sanity
checks, then run controlled engine matches before claiming improved strength.
Version 1 ignores en passant, move counters and history; it is not incremental
NNUE and will evaluate much more slowly than the handcrafted evaluator.
