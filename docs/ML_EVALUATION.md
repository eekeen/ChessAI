# ML evaluation and deployment

## Development history

V1 learned direct evaluation from 773 inputs: twelve 64-square piece planes, side to move and four castling flags. V2 retains those inputs and adds 16 material/count, phase, bishop-pair and king/castling features, for 789 inputs. The exact ordering and normalization are versioned in [the schema](../ml/feature_schema_v2.json) and the corresponding Python/C++ feature code.

V2 uses a 789 -> 128 -> 64 -> 1 network with two ReLUs. Training uses PyTorch offline; inference uses exported C++ arrays. A direct model predicts White-relative centipawns. The residual model instead learns `Stockfish label - Classic`, with target scaling of 1000. Production applies `round(clip(Classic + 0.25 * residual, -1500, 1500))`.

Production residual ID: `v2-residual-3fb0a29e8514af8c`. Direct V2 ID: `v2-direct-3b6bb568881c6bd0`. Alpha is frozen at 0.25; it is not encoded in the model ID. The generated weight headers must be committed for a reproducible production build. Training checkpoints and raw data are local intermediates, not runtime dependencies.

## Data and model selection

The original 250,000-position corpus uses Stockfish labels from Lichess evaluation data. Preprocessing bounds the raw-record scan, deduplicates usable positions and uses stratified reservoir sampling. V2 conversion retains labels, FENs and split IDs. Validation and test splits contain 24,997 positions each. Checkpoints were selected using validation loss, not the test split. See [training workflow](../ml/README_V2.md) and [recorded metrics](../ml/V2_RESULTS.md).

The recorded V1 Direct test MAE was 298.45 cp, V2 Direct Huber 258.67 cp and the full residual correction experiment 256.91 cp, versus Classic 452.93 cp. Those residual metrics describe the historical full correction experiment, **not production alpha 0.25**. Classic was better on near-equal positions. Related positions can cross dataset splits; the bounded stratified sample is not a natural game distribution.

Lower label error alone did not establish playing strength. Development matches exposed that distinction. The 16-opening development set supported tuning, and the 32-opening held-out validation set compared alpha 0.10 and 0.25. The candidate was frozen at 0.25 before the distinct 64-opening final suite. No new tuning is authorized by the release work.

## Native inference and verification

The optimized production path combines an active-index sparse first layer with an AVX2 fused second-layer/ReLU/output tail. It preserves each neuron's accumulation order and output order; separate multiply/add instructions avoid contraction changes. CPU/OS checks retain portable reference fallback. No runtime PyTorch installation is needed by the engine or GUI.

Python/C++ feature parity is exact. Raw neural outputs are compared within 0.02 cp because library arithmetic can differ. Separately, optimized/reference **C++** residuals are bit-identical across all 250,000 positions, with zero changed rounded production scores. Profiler decomposition parity and fixed-depth search regressions provide additional checks. These tests do not retrain or reselect a model.

Full-corpus reproduction needs the local dataset and checkpoints; a source checkout contains the deployed headers, feature schema and synthetic regression fixtures. See [release check commands](RELEASE_CHECK.md).
