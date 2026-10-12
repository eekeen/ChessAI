# Measured evaluator performance

Performance only; these are not playing-strength results.

Machine: AMD Ryzen 7 3700X 8-Core Processor; Windows-10-10.0.19045-SP0. Build: Release, MSVC-19.28.29914.0.
Hybrid alpha: 0.25; model: `v2-residual-3fb0a29e8514af8c`.
Manifest: `performance-middlegames-v1`, SHA-256 `da829c823df87a0aa6f8cbf436093b4a526019c8ec68111cea8fe28e1573e9c7`.
16 positions, 3 repetitions; one search thread. UTC: 2026-09-25T14:08:42.981589+00:00.

## Static evaluation

| Evaluator | Evaluations/sec | Average latency us | Batch latency std us | Slowdown |
|---|---:|---:|---:|---:|
| classic | 2,786,906 | 0.359 | 0.006 | 1.00x |
| ml | 134,586 | 7.430 | 0.023 | 20.71x |
| hybrid | 319,561 | 3.129 | 0.028 | 8.72x |

## Search at equal wall-clock budgets

| Budget ms | Evaluator | Avg completed depth | Depth delta vs Classic | Avg nodes | Nodes/sec | Total nodes | TT hits | Elapsed s |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 100 | classic | 2.562 | +0.000 | 10,519 | 105,181 | 504,932 | 4,676 | 4.801 |
| 100 | ml | 2.583 | +0.021 | 7,035 | 70,314 | 337,669 | 2,843 | 4.802 |
| 100 | hybrid | 2.625 | +0.062 | 8,816 | 88,130 | 423,160 | 3,783 | 4.802 |
| 250 | classic | 3.125 | +0.000 | 25,211 | 100,838 | 1,210,124 | 13,155 | 12.001 |
| 250 | ml | 3.125 | +0.000 | 17,297 | 69,170 | 830,261 | 10,235 | 12.003 |
| 250 | hybrid | 3.062 | -0.062 | 21,406 | 85,610 | 1,027,465 | 12,599 | 12.002 |
| 1000 | classic | 4.083 | +0.000 | 105,871 | 105,869 | 5,081,803 | 69,775 | 48.001 |
| 1000 | ml | 4.021 | -0.062 | 70,718 | 70,713 | 3,394,454 | 52,723 | 48.003 |
| 1000 | hybrid | 4.125 | +0.042 | 87,244 | 87,237 | 4,187,709 | 58,641 | 48.004 |

## Per-position completed depths

Each cell: mean [min–max] across repetitions. Raw nodes, elapsed time, TT hits and moves are in JSON.

| Budget ms | Position | Classic | ML | Hybrid |
|---|---|---:|---:|---:|
| 100 | test-row-102601 | 3.00 [3–3] | 3.00 [3–3] | 2.67 [2–3] |
| 100 | test-row-30972 | 3.00 [3–3] | 2.00 [2–2] | 3.00 [3–3] |
| 100 | test-row-181614 | 3.00 [3–3] | 3.00 [3–3] | 3.00 [3–3] |
| 100 | test-row-155835 | 4.00 [4–4] | 3.67 [3–4] | 4.00 [4–4] |
| 100 | test-row-230080 | 0.00 [0–0] | 1.00 [1–1] | 2.00 [2–2] |
| 100 | test-row-200427 | 3.00 [3–3] | 3.00 [3–3] | 3.00 [3–3] |
| 100 | test-row-225258 | 3.00 [3–3] | 2.00 [2–2] | 3.00 [3–3] |
| 100 | test-row-237767 | 3.00 [3–3] | 3.00 [3–3] | 3.00 [3–3] |
| 100 | test-row-87149 | 4.00 [4–4] | 3.00 [3–3] | 3.00 [3–3] |
| 100 | test-row-232470 | 2.00 [2–2] | 3.00 [3–3] | 1.00 [1–1] |
| 100 | test-row-81274 | 2.00 [2–2] | 2.67 [2–3] | 3.00 [3–3] |
| 100 | test-row-105646 | 3.00 [3–3] | 3.00 [3–3] | 2.67 [2–3] |
| 100 | test-row-117849 | 3.00 [3–3] | 2.00 [2–2] | 3.00 [3–3] |
| 100 | test-row-9232 | 1.00 [1–1] | 2.00 [2–2] | 1.00 [1–1] |
| 100 | test-row-132289 | 1.00 [1–1] | 2.00 [2–2] | 1.67 [1–2] |
| 100 | test-row-136078 | 3.00 [3–3] | 3.00 [3–3] | 3.00 [3–3] |
| 250 | test-row-102601 | 4.00 [4–4] | 4.00 [4–4] | 4.00 [4–4] |
| 250 | test-row-30972 | 3.00 [3–3] | 3.00 [3–3] | 3.00 [3–3] |
| 250 | test-row-181614 | 4.00 [4–4] | 4.00 [4–4] | 4.00 [4–4] |
| 250 | test-row-155835 | 4.00 [4–4] | 4.00 [4–4] | 4.00 [4–4] |
| 250 | test-row-230080 | 2.00 [2–2] | 2.00 [2–2] | 2.00 [2–2] |
| 250 | test-row-200427 | 3.00 [3–3] | 3.00 [3–3] | 3.00 [3–3] |
| 250 | test-row-225258 | 3.00 [3–3] | 3.00 [3–3] | 3.00 [3–3] |
| 250 | test-row-237767 | 4.00 [4–4] | 3.00 [3–3] | 4.00 [4–4] |
| 250 | test-row-87149 | 4.00 [4–4] | 4.00 [4–4] | 4.00 [4–4] |
| 250 | test-row-232470 | 2.00 [2–2] | 3.00 [3–3] | 2.00 [2–2] |
| 250 | test-row-81274 | 3.00 [3–3] | 3.00 [3–3] | 3.00 [3–3] |
| 250 | test-row-105646 | 3.00 [3–3] | 3.00 [3–3] | 3.00 [3–3] |
| 250 | test-row-117849 | 3.00 [3–3] | 2.00 [2–2] | 3.00 [3–3] |
| 250 | test-row-9232 | 2.00 [2–2] | 3.00 [3–3] | 2.00 [2–2] |
| 250 | test-row-132289 | 2.00 [2–2] | 3.00 [3–3] | 2.00 [2–2] |
| 250 | test-row-136078 | 4.00 [4–4] | 3.00 [3–3] | 3.00 [3–3] |
| 1000 | test-row-102601 | 4.33 [4–5] | 5.00 [5–5] | 4.00 [4–4] |
| 1000 | test-row-30972 | 4.00 [4–4] | 3.00 [3–3] | 4.00 [4–4] |
| 1000 | test-row-181614 | 5.00 [5–5] | 4.67 [4–5] | 5.00 [5–5] |
| 1000 | test-row-155835 | 6.00 [6–6] | 5.00 [5–5] | 5.00 [5–5] |
| 1000 | test-row-230080 | 3.00 [3–3] | 3.00 [3–3] | 3.00 [3–3] |
| 1000 | test-row-200427 | 4.00 [4–4] | 4.00 [4–4] | 4.00 [4–4] |
| 1000 | test-row-225258 | 4.00 [4–4] | 4.00 [4–4] | 4.00 [4–4] |
| 1000 | test-row-237767 | 4.00 [4–4] | 4.00 [4–4] | 5.00 [5–5] |
| 1000 | test-row-87149 | 5.00 [5–5] | 5.00 [5–5] | 5.00 [5–5] |
| 1000 | test-row-232470 | 3.00 [3–3] | 3.00 [3–3] | 3.00 [3–3] |
| 1000 | test-row-81274 | 4.00 [4–4] | 4.00 [4–4] | 4.00 [4–4] |
| 1000 | test-row-105646 | 4.00 [4–4] | 4.00 [4–4] | 4.00 [4–4] |
| 1000 | test-row-117849 | 4.00 [4–4] | 3.00 [3–3] | 4.00 [4–4] |
| 1000 | test-row-9232 | 3.00 [3–3] | 4.00 [4–4] | 3.00 [3–3] |
| 1000 | test-row-132289 | 3.00 [3–3] | 4.00 [4–4] | 4.00 [4–4] |
| 1000 | test-row-136078 | 5.00 [5–5] | 4.67 [4–5] | 5.00 [5–5] |

## Interpretation

Hybrid static evaluation took 8.72x Classic's latency on this machine. The learned-evaluation path is therefore the clearest measured added cost and the next profiling target. This benchmark does not separate feature extraction from neural matrix operations, so it cannot identify which internal kernel dominates. See V2_OPTIMIZATION.md when comparing reference and optimized inference builds.

Search trees differ with evaluator scores: nodes/sec and completed depth measure the combined evaluator/search behavior, not inference cost alone. Nodes and TT hits include work in the last interrupted iteration; depth counts only completed iterations. TT clearing, position loading, warm-up and reporting are excluded from measured search times. Actual elapsed time is used for throughput, including budget overshoot and early mate exits. Static latency is batch-average wall time including feature extraction, clipping, and loop overhead; it is not a per-call latency percentile. CPU scheduling, clocks and load affect results. These timings are specific to this machine/build.

At 100 ms, Hybrid completed +0.062 plies versus Classic on average, with 0.838x its search nodes/sec.
At 250 ms, Hybrid completed -0.062 plies versus Classic on average, with 0.849x its search nodes/sec.
At 1000 ms, Hybrid completed +0.042 plies versus Classic on average, with 0.824x its search nodes/sec.
