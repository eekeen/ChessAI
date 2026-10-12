# Measured evaluator performance

Performance only; these are not playing-strength results.

Machine: AMD Ryzen 7 3700X 8-Core Processor; Windows-10-10.0.19045-SP0. Build: Release, MSVC-19.28.29914.0.
Hybrid alpha: 0.25; model: `v2-residual-3fb0a29e8514af8c`.
Manifest: `performance-middlegames-v1`, SHA-256 `da829c823df87a0aa6f8cbf436093b4a526019c8ec68111cea8fe28e1573e9c7`.
16 positions, 3 repetitions; one search thread. UTC: 2026-09-25T13:59:03.205063+00:00.

## Static evaluation

| Evaluator | Evaluations/sec | Average latency us | Batch latency std us | Slowdown |
|---|---:|---:|---:|---:|
| classic | 2,888,520 | 0.346 | 0.006 | 1.00x |
| ml | 135,386 | 7.386 | 0.044 | 21.34x |
| hybrid | 324,043 | 3.086 | 0.027 | 8.91x |

## Search at equal wall-clock budgets

| Budget ms | Evaluator | Avg completed depth | Depth delta vs Classic | Avg nodes | Nodes/sec | Total nodes | TT hits | Elapsed s |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | classic | 0.271 | +0.000 | 101 | 99,829 | 4,830 | 12 | 0.048 |
| 1 | ml | 0.125 | -0.146 | 63 | 60,470 | 3,006 | 5 | 0.050 |
| 1 | hybrid | 0.188 | -0.083 | 81 | 79,672 | 3,902 | 7 | 0.049 |

## Per-position completed depths

Each cell: mean [min–max] across repetitions. Raw nodes, elapsed time, TT hits and moves are in JSON.

| Budget ms | Position | Classic | ML | Hybrid |
|---|---|---:|---:|---:|
| 1 | test-row-102601 | 0.00 [0–0] | 0.00 [0–0] | 0.00 [0–0] |
| 1 | test-row-30972 | 1.00 [1–1] | 0.00 [0–0] | 0.67 [0–1] |
| 1 | test-row-181614 | 0.67 [0–1] | 1.00 [1–1] | 1.00 [1–1] |
| 1 | test-row-155835 | 0.00 [0–0] | 0.00 [0–0] | 0.00 [0–0] |
| 1 | test-row-230080 | 0.00 [0–0] | 0.00 [0–0] | 0.00 [0–0] |
| 1 | test-row-200427 | 0.33 [0–1] | 0.00 [0–0] | 0.00 [0–0] |
| 1 | test-row-225258 | 0.00 [0–0] | 0.00 [0–0] | 0.00 [0–0] |
| 1 | test-row-237767 | 0.00 [0–0] | 0.00 [0–0] | 0.00 [0–0] |
| 1 | test-row-87149 | 1.00 [1–1] | 0.00 [0–0] | 0.33 [0–1] |
| 1 | test-row-232470 | 0.00 [0–0] | 0.00 [0–0] | 0.00 [0–0] |
| 1 | test-row-81274 | 0.33 [0–1] | 0.00 [0–0] | 0.00 [0–0] |
| 1 | test-row-105646 | 1.00 [1–1] | 0.00 [0–0] | 0.00 [0–0] |
| 1 | test-row-117849 | 0.00 [0–0] | 0.00 [0–0] | 1.00 [1–1] |
| 1 | test-row-9232 | 0.00 [0–0] | 0.00 [0–0] | 0.00 [0–0] |
| 1 | test-row-132289 | 0.00 [0–0] | 0.00 [0–0] | 0.00 [0–0] |
| 1 | test-row-136078 | 0.00 [0–0] | 1.00 [1–1] | 0.00 [0–0] |

## Interpretation

Hybrid static evaluation took 8.91x Classic's latency on this machine. The learned-evaluation path is therefore the clearest measured added cost and the next profiling target. This benchmark does not separate feature extraction from neural matrix operations, so it cannot identify which internal kernel dominates. See V2_OPTIMIZATION.md when comparing reference and optimized inference builds.

Search trees differ with evaluator scores: nodes/sec and completed depth measure the combined evaluator/search behavior, not inference cost alone. Nodes and TT hits include work in the last interrupted iteration; depth counts only completed iterations. TT clearing, position loading, warm-up and reporting are excluded from measured search times. Actual elapsed time is used for throughput, including budget overshoot and early mate exits. Static latency is batch-average wall time including feature extraction, clipping, and loop overhead; it is not a per-call latency percentile. CPU scheduling, clocks and load affect results. These timings are specific to this machine/build.

At 1 ms, Hybrid completed -0.083 plies versus Classic on average, with 0.798x its search nodes/sec.
