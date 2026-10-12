# Benchmarks and interpretation

## Correctness and offline accuracy

Perft checks legal move generation, not playing strength. Starting-position counts at depths 1-5 are 20, 400, 8,902, 197,281 and 4,865,609. Kiwipete at depths 1-4 is 48, 2,039, 97,862 and 4,085,603.

[Offline model metrics](../ml/V2_RESULTS.md) measure prediction error against labels. They do not substitute for matches. Historical full-residual metrics must not be described as production alpha-0.25 metrics. [ML evaluation](ML_EVALUATION.md) explains dataset and parity limitations.

## Inference and search performance

Historical Release measurements on Ryzen 7 3700X: reference Hybrid 7.563 us/eval (132,231 eval/s), optimized 3.031 us/eval (329,902 eval/s): 59.9% lower latency, approximately 2.50x throughput. Production uses AVX2 fused tail plus active-index sparse Linear1, with reference fallback. All 250,000 optimized residuals and rounded scores matched reference.

| Move budget | Reference nodes/s | Optimized nodes/s | Reference average depth | Optimized average depth |
|---|---:|---:|---:|---:|
| 100 ms | 63,385 | 88,130 | 2.208 | 2.625 |
| 250 ms | 67,080 | 85,610 | 2.938 | 3.062 |
| 1000 ms | 67,415 | 87,237 | 4.000 | 4.125 |

Timing varies with load and hardware. Isolated profiler stages include instrumentation and controls and are not simply additive. Static throughput does not equal match strength. [Optimization report](../benchmarks/optimization_results.md), [methodology](../benchmarks/V2_OPTIMIZATION.md) and [performance guide](../benchmarks/PERFORMANCE.md) retain the original evidence and caveats.

## Separate opening roles

| Suite | Positions | Role |
|---|---:|---|
| `common-openings-v1` | 16 | Development and alpha tuning; no longer held out |
| `heldout-openings-v1` | 32 | Validation comparison of alpha 0.10 and 0.25; now consumed |
| `final-openings-v1` | 64 | Frozen internal final candidate evaluation, alpha 0.25 |
| External `openings-v1` | 64 | Separately frozen external Stockfish calibration |

Suites use paired colors. Internal final overlap checks include normalized endpoint FENs and intermediate positions in earlier suites. External manifests and protocols are separately versioned. No suite is modified after inspecting results. Existing results are historical evidence, not instructions to rerun experiments or tune alpha.

## Frozen internal final results

Hybrid versus Classic, alpha 0.25, 128 games per experiment:

| Search condition | Hybrid W / D / L | Score | Opening-cluster 95% score CI | Hybrid Elo difference | Average plies |
|---|---:|---:|---:|---:|---:|
| Fixed depth 3 | 37 / 74 / 17 | 57.81% | 52.34-63.28% | +54.74 | 84.62 |
| 250 ms/move | 40 / 62 / 26 | 55.47% | 49.61-61.33% | +38.15 | 96.38 |

The fixed-depth interval supports an advantage within this protocol; the timed interval includes equality and does not establish a significant improvement. Neither generalizes automatically to arbitrary openings or hardware. Elo transforms the match score; it is not an absolute rating. Paired openings are bootstrap clusters, not independent games. See [depth result](../benchmarks/final_v1_alpha025_depth3.json), [timed result](../benchmarks/final_v1_alpha025_250ms.json) and [frozen protocol](../benchmarks/FINAL.md).

## External Stockfish calibration

Stockfish 19, Threads=1, Hash=64 MiB, 250 ms/move, 64 held-out positions with colors reversed, 128 games per level, 512 final games. Hybrid uses the same frozen alpha/model.

| Stockfish UCI_Elo | ChessAI W / D / L | Score | Opening-cluster 95% score CI |
|---|---:|---:|---:|
| 1520 | 78 / 18 / 32 | 67.97% | 60.55-75.39% |
| 1620 | 58 / 19 / 51 | 52.73% | 44.91-60.94% |
| 1720 | 46 / 24 / 58 | 45.31% | 37.50-52.73% |
| 1820 | 34 / 13 / 81 | 31.64% | 23.44-40.62% |

**Observed Stockfish 19 UCI_Elo crossing of approximately 1657 at 250 ms/move under the frozen calibration protocol.** Linear interpolation gives 1656.84. This is not FIDE, Chess.com, Lichess or universal engine Elo.

Bootstrap resampling preserves both colors jointly across opponent levels. Only 89.94% of replicates identified a crossing; the bracket was insufficiently stable for a reliable calibrated point estimate and 95% interval. Both remain null in the report. Per-level score intervals do not remedy that limitation. The fixed suite, timed-search variability and Stockfish strength-limited randomness constrain interpretation.

[Final report](../benchmarks/elo/final_results.md), [game records](../benchmarks/elo/final_results.json), [frozen protocol](../benchmarks/elo/calibration_protocol.json) and [calibration framework](../benchmarks/elo/README.md). No frozen strength matches were rerun for release preparation.
