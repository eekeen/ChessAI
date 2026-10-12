# Measured V2 results on the original 250,000 positions

The original V1 checkpoint and dataset are preserved. V2 conversion preserved
all labels, FENs, split IDs, depths and the original 773 feature values. No new
positions were sampled. There are 24,997 validation and 24,997 test positions.

Two matched experiments used 789 inputs, 128/64 hidden units, dropout 0.10,
AdamW weight decay 0.0001, learning rate 0.001, batch size 512 and seed 42.
Huber delta was 300 cp. Each direct/residual network selected its own best
checkpoint by validation loss, with patience 8. The test split and material
sanity suite were not training data or checkpoint-selection criteria.

| Evaluator | Best epoch | Validation MAE | Validation RMSE | Test MAE | Test RMSE |
|---|---:|---:|---:|---:|---:|
| V1 Direct | 6 | 297.58 | 452.42 | 298.45 | 455.21 |
| Classic | — | 456.84 | 655.87 | 452.93 | 655.27 |
| V2 Direct, Huber | 16 | 258.78 | 443.24 | 258.67 | 444.52 |
| V2 Residual Hybrid, Huber | 18 | 258.02 | 440.53 | 256.91 | 439.80 |
| V2 Direct, MSE | 8 | 282.61 | 438.44 | 283.88 | 444.64 |
| V2 Residual Hybrid, MSE | 7 | 284.00 | 440.89 | 283.26 | 441.82 |

Scores are raw White-relative centipawns, directly comparable with the original
V1 report. Deployed Huber Hybrid clips the final sum to +/-1500 cp; its clipped
test MAE/RMSE is 251.39/438.09 cp before integer rounding. Huber was retained for
the default V2 headers for its lower validation MAE; this is not a claim that it
wins more games than MSE or Classic. All experiment checkpoints are kept.

## Starting-position material sanity (White to move)

| Evaluator | Start | Without White queen | Shift | Without Black queen | Shift |
|---|---:|---:|---:|---:|---:|
| V1 Direct | -30.76 | -218.44 | -187.68 | 99.05 | 129.82 |
| Classic | 0.00 | -895.00 | -895.00 | 895.00 | 895.00 |
| V2 Direct, Huber | 61.54 | -591.46 | -653.00 | 336.48 | 274.95 |
| V2 Residual Hybrid, Huber | 19.14 | -659.94 | -679.08 | 779.96 | 760.82 |

Hybrid passes the 300 cp queen-removal shifts with either side to move.
Direct still fails the Black-queen shift threshold. The broader Huber residual
suite fails one simplified White-queen-versus-king shift threshold (189 cp versus
300 required); the MSE residual passes all material-suite gates. These are
directional validation heuristics, not exact Stockfish labels.

## Huber test metrics by target range (MAE / RMSE cp)

| Target range | Count | Classic | V2 Direct | V2 Residual Hybrid |
|---|---:|---:|---:|---:|
| absolute score <100 | 3,566 | 86.83 / 141.57 | 158.37 / 306.79 | 161.78 / 313.58 |
| 100 to <800 | 14,288 | 279.36 / 355.05 | 232.04 / 330.94 | 228.24 / 331.14 |
| >=800 | 7,143 | 982.89 / 1113.75 | 362.00 / 652.26 | 361.76 / 639.12 |

Classic remains substantially better on roughly equal positions. Training loss
continues to decrease beyond the selected epochs, so regularization reduces some
errors but does not eliminate overfitting. The bounded, balanced prefix is not a
natural game-position distribution, and closely related positions may cross splits.
Lower label error is not measured playing-strength improvement.

Full reports, histories and plots are in `ml/models/v2_huber/` and
`ml/models/v2_mse/`, with separate direct and residual checkpoints.

## Validation and implementation files

Both no-model and V1/V2 model-present builds passed the existing perft and search
tests. V1 feature/inference parity remains valid. V2 compares 264 positions across
all 789 float32 features exactly. Maximum raw C++/PyTorch prediction error was
0.001342 cp for Direct and 0.001464 cp for Residual. Final Hybrid addition,
clipping/rounding, protocol behavior and hidden Tkinter construction were verified.
The GUI enables all three modes and defaults to Hybrid with the current headers.

V2 files added:

- `ml/feature_schema_v2.json`, `ml/features_v2.py`, `ml/generate_feature_schema.py`
- `ml/prepare_v2.py`, `ml/model_v2.py`, `ml/train_v2.py`, `ml/export_v2.py`
- `ml/material_sanity.py`, `ml/verify_v2.py`, `ml/README_V2.md`, `ml/V2_RESULTS.md`
- `src/engine/FeatureSchemaV2.h`, `src/engine/MLEvaluationV2.h`, `src/engine/MLEvaluationV2.cpp`

Existing integration files updated for V2:

- `src/engine/PositionEvaluator.h`, `src/engine/PositionEvaluator.cpp`
- `src/main.cpp`, `src/gui/gui.py`
- `tests/eval_tool.cpp`, `tests/evaluation_tests.cpp`, `ml/test_protocol.py`
- `CMakeLists.txt`, `.gitignore`, `README.md`, `ml/README.md`

Generated artifacts include `ml/data/lichess_250k_v2.npz`, its metadata, both
experiment directories and the two ignored V2 C++ weight headers. V1 code and
`ml/models/best.pt` were retained. No model or training changes were needed for
the subsequently added [headless tournament](../benchmarks/README.md).

The next strength experiment is the 200-game Classic–Hybrid command in that
tournament guide. It has **not** been run; the short tournament smoke fixtures
are not evidence of playing strength.
