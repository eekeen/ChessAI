# V2: explicit material features and residual evaluation

Actual results from both completed 250k experiments are recorded in
[V2_RESULTS.md](V2_RESULTS.md), including limitations and failed sanity gates.

V1 remains available unchanged through `features.py`, `model.py`,
`train_evaluator.py`, `export_model.py`, and `MLEvaluation.cpp`. Its original
checkpoint and 250k NPZ are preserved locally but excluded from publication.
Recorded metrics, dataset metadata and V2 learning histories are included; a
fresh source checkout must prepare its own datasets and checkpoints. V2 writes separate
datasets, checkpoints and headers. This experiment does not increase the dataset
or scan the Lichess dump again.

## Features: 789 inputs

The first 773 values are identical to V1. `feature_schema_v2.json` defines all
16 appended scalars, their order, constants and operations. `features_v2.py`
interprets it; `generate_feature_schema.py` generates the committed C++
`FeatureSchemaV2.h`. `--check` detects drift. The two inference implementations
are compared on complete float32 vectors, including all new features.

| Indices | Features | Scaling |
|---|---|---|
| 773–777 | White pawn, knight, bishop, rook, queen counts | Divide by 8, 2, 2, 2, 1 |
| 778–782 | Black counts, same order | Same divisors |
| 783 | White minus Black material | Values 100/320/330/500/900; divide by 4000 |
| 784 | Remaining non-pawn phase | N/B=1, R=2, Q=4 per piece; divide by 24, cap at 1 |
| 785–786 | White/Black bishop pair | At least two bishops (including promotions) |
| 787–788 | White/Black castled king location | King on c1/g1 or c8/g8 |

Counts may exceed 1 after promotion; material balance is signed and not clipped.
Castled king flags are **location proxies**, not proof of castling history (FEN
cannot supply that history). Phase is 1 at the start and 0 for a pawn ending.

## Exact residual targets without duplicating Classic

First build the C++ helper from a Visual Studio developer shell with CMake on PATH:

```powershell
cmake -S . -B build -A x64
cmake --build build --config Release
python ml/prepare_v2.py --data ml/data/lichess_250k.npz --output ml/data/lichess_250k_v2.npz --tool build/Release/eval_tool.exe
```

`eval_tool classic` accepts one six-field FEN per line and emits exact handcrafted
White cp. Conversion uses one process for all positions; four-field dataset FENs
receive default counters. Stockfish `y`, FEN order, depths and split IDs are
unchanged. The output adds float32 V2 `X`, `classic` and `residual = y - classic`.
It embeds source NPZ hash, helper executable hash, and feature schema hash. The
original NPZ cannot be overwritten by this conversion. No Classic formula or
piece-square table is duplicated in Python.

Targets in the source NPZ were already clipped to +/-1500 cp. Residuals are **not
clipped**: a large handcrafted advantage can legitimately require a large negative
correction. The input still omits en passant, move counters and history.

## Matched direct and residual training

```powershell
python ml/train_v2.py --data ml/data/lichess_250k_v2.npz --baseline ml/models/best.pt --output-dir ml/models/v2_huber --loss huber --weight-decay 0.0001 --dropout 0.10 --epochs 60 --patience 8
```

This trains **two separate networks**: Direct predicts `y/1000`; Residual predicts
`(y-classic)/1000`. Both use 789 -> Linear 128 -> ReLU -> Dropout -> Linear 64 ->
ReLU -> Linear 1. Dropout is training-only. AdamW's weight decay is explicit;
V1 already used AdamW but implicitly used its default weight decay. All new
regularization settings are configurable. Huber is the V2 default, with delta
0.3 normalized units (300 cp); `--loss mse` preserves the alternative objective.

Each run must use a fresh output directory to avoid destroying prior experiments.
Seeds control initialization, shuffling and dropout. CPU/CUDA selection remains
automatic (`--device cpu` or `--device cuda` overrides it). Deterministic algorithms
are enabled; floating-point results can vary with hardware/thread count/version.

Both networks use only the original training split. Each checkpoint is chosen by
its validation objective, with early stopping; no test or sanity examples are used
for checkpoint selection or training. After both models finish, the best checkpoints
are reloaded and evaluated once on the original test split. `--baseline` recomputes
V1 on these same splits and checks that its training dataset hash matches the source.

Outputs:

- `direct_best.pt`, `residual_best.pt`: independent best validation checkpoints.
- `direct_history.json`, `residual_history.json`: train and validation learning curves.
- `comparison.json`: validation/test MAE and RMSE for Direct, Classic, Residual Hybrid,
  and optional V1; score-range results; sanity predictions; experiment provenance.
- `comparison.png`: test predictions versus targets and residual error distributions.

Reports include raw scores for comparison with the original V1 report and clipped
scores matching deployment. Range metrics use Stockfish target absolute values:
less than 100, 100 inclusive to 800 exclusive, and at least 800 cp. Classic's actual
runtime score remains unclipped; its raw metric is the primary Classic benchmark.

The automatically generated sanity suite covers both sides to move, missing queens,
rooks, knights and bishops, plus legal simplified positions. It reports direction
and shift relative to each corresponding anchor, not fabricated Stockfish targets.
Queen shifts have a 300 cp minimum, rooks 150 and starting-position minor removals
80. Lone-minor simplified endings are report-only, since they cannot force mate.

For an MSE comparison use a fresh output directory:

```powershell
python ml/train_v2.py --baseline ml/models/best.pt --output-dir ml/models/v2_mse --loss mse --epochs 60 --patience 8 --threads 2
```

Do not tune against the held-out test set. Choose an objective using validation
metrics and report all completed experiments, including tradeoffs.

## C++ export, integration and regression checks

The export commands below are the historical research workflow and require local
checkpoints. Run exports in a separate research checkout/build to preserve the
bundled production headers. Normal users build the committed headers directly;
see [current release checks](../docs/RELEASE_CHECK.md).

```powershell
python ml/export_v2.py --checkpoint ml/models/v2_huber/direct_best.pt
python ml/export_v2.py --checkpoint ml/models/v2_huber/residual_best.pt
cmake --build build --config Release --clean-first
python ml/verify_v2.py --tool build/Release/eval_tool.exe --direct ml/models/v2_huber/direct_best.pt --residual ml/models/v2_huber/residual_best.pt --data ml/data/lichess_250k_v2.npz
python ml/verify_cpp.py --tool build/Release/eval_tool.exe
python ml/test_pipeline.py
python ml/test_protocol.py --engine build/Release/ChessAI.exe
Push-Location build
ctest -C Release --output-on-failure
Pop-Location
```

The two generated headers are `DirectWeightsV2.h` and `ResidualWeightsV2.h`.
They embed architecture, scale, model kind/hash and a compile-time schema check.
Synthetic V2 checkpoints are rejected by export. To test without installing, use
`--output-dir ml/models/<experiment>/cpp` and configure a separate build with
`-DCHESSAI_V2_MODEL_DIR=<absolute directory>`. Always rebuild when optional headers
are added or removed. C++ has no Python or ML-library runtime dependency.

Runtime selection is centralized in `PositionEvaluator`:

- Classic: unchanged handcrafted evaluator.
- ML: V2 direct model, or V1 direct model when only V1 is compiled in.
- Historical full-correction Hybrid: **Classic + dedicated V2 residual**.
  Production subsequently froze **Classic + 0.25 * residual**; see
  [deployment details](../docs/ML_EVALUATION.md).
  The sum is clipped to +/-1500 cp and rounded after addition, safely outside the
  search mate band. If only V1 is installed, its old weighted hybrid remains
  available for baseline benchmarking.

Without the relevant weights, modes are explicitly unavailable. `evalmodes` lists
supported modes, so the GUI correctly enables direct-only/residual-only combinations.
Hybrid is the default when available, otherwise Classic. Mode changes still clear
the TT. Protocol, move generation, search algorithms, book and difficulty behavior
remain intact. `model` reports the residual V2 identifier when installed, otherwise
the direct V2 or legacy V1 identifier.

The original V1 exporter/header can still be used in a separate build through
`CHESSAI_ML_WEIGHTS_HEADER`. Point `CHESSAI_V2_MODEL_DIR` at an empty directory for
a V1-only comparison once normal V2 headers have been installed.

No MAE improvement alone establishes stronger chess play or calibrated Elo.
