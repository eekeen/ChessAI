# Measured evaluator performance

Performance only; these are not playing-strength results.

Machine: AMD Ryzen 7 3700X 8-Core Processor; Windows-10-10.0.19045-SP0. Build: Release, MSVC-19.28.29914.0.
Hybrid alpha: 0.25; model: `v2-residual-3fb0a29e8514af8c`.
Manifest: `performance-middlegames-v1`, SHA-256 `da829c823df87a0aa6f8cbf436093b4a526019c8ec68111cea8fe28e1573e9c7`.
16 positions, 3 repetitions; one search thread. UTC: 2026-09-25T09:12:12.171592+00:00.

## Static evaluation

| Evaluator | Evaluations/sec | Average latency us | Batch latency std us | Slowdown |
|---|---:|---:|---:|---:|
| classic | 2,742,075 | 0.365 | 0.006 | 1.00x |
| ml | 138,699 | 7.210 | 0.035 | 19.77x |
| hybrid | 295,895 | 3.380 | 0.011 | 9.27x |

## Search at equal wall-clock budgets

| Budget ms | Evaluator | Avg completed depth | Depth delta vs Classic | Avg nodes | Nodes/sec | Total nodes | TT hits | Elapsed s |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 100 | classic | 2.562 | +0.000 | 10,913 | 109,119 | 523,823 | 4,812 | 4.800 |
| 100 | ml | 2.625 | +0.062 | 7,355 | 73,519 | 353,050 | 3,138 | 4.802 |
| 100 | hybrid | 2.667 | +0.104 | 9,052 | 90,494 | 434,494 | 3,815 | 4.801 |
| 250 | classic | 3.229 | +0.000 | 27,922 | 111,682 | 1,340,233 | 14,321 | 12.000 |
| 250 | ml | 3.125 | -0.104 | 18,990 | 75,942 | 911,506 | 11,712 | 12.003 |
| 250 | hybrid | 3.167 | -0.062 | 22,759 | 91,025 | 1,092,436 | 13,303 | 12.002 |
| 1000 | classic | 4.333 | +0.000 | 124,937 | 124,936 | 5,996,985 | 89,525 | 48.000 |
| 1000 | ml | 4.167 | -0.167 | 81,961 | 81,957 | 3,934,137 | 68,338 | 48.002 |
| 1000 | hybrid | 4.167 | -0.167 | 100,370 | 100,367 | 4,817,748 | 70,385 | 48.001 |

## Per-position completed depths

Each cell: mean [min–max] across repetitions. Raw nodes, elapsed time, TT hits and moves are in JSON.

| Budget ms | Position | Classic | ML | Hybrid |
|---|---|---:|---:|---:|
| 100 | test-row-102601 | 3.00 [3–3] | 3.00 [3–3] | 3.00 [3–3] |
| 100 | test-row-30972 | 3.00 [3–3] | 2.00 [2–2] | 3.00 [3–3] |
| 100 | test-row-181614 | 3.00 [3–3] | 3.00 [3–3] | 3.00 [3–3] |
| 100 | test-row-155835 | 4.00 [4–4] | 4.00 [4–4] | 4.00 [4–4] |
| 100 | test-row-230080 | 0.00 [0–0] | 1.00 [1–1] | 2.00 [2–2] |
| 100 | test-row-200427 | 3.00 [3–3] | 3.00 [3–3] | 3.00 [3–3] |
| 100 | test-row-225258 | 3.00 [3–3] | 2.00 [2–2] | 3.00 [3–3] |
| 100 | test-row-237767 | 3.00 [3–3] | 3.00 [3–3] | 3.00 [3–3] |
| 100 | test-row-87149 | 4.00 [4–4] | 3.00 [3–3] | 3.00 [3–3] |
| 100 | test-row-232470 | 2.00 [2–2] | 3.00 [3–3] | 1.00 [1–1] |
| 100 | test-row-81274 | 2.00 [2–2] | 3.00 [3–3] | 3.00 [3–3] |
| 100 | test-row-105646 | 3.00 [3–3] | 3.00 [3–3] | 3.00 [3–3] |
| 100 | test-row-117849 | 3.00 [3–3] | 2.00 [2–2] | 3.00 [3–3] |
| 100 | test-row-9232 | 1.00 [1–1] | 2.00 [2–2] | 1.00 [1–1] |
| 100 | test-row-132289 | 1.00 [1–1] | 2.00 [2–2] | 1.67 [1–2] |
| 100 | test-row-136078 | 3.00 [3–3] | 3.00 [3–3] | 3.00 [3–3] |
| 250 | test-row-102601 | 4.00 [4–4] | 4.00 [4–4] | 4.00 [4–4] |
| 250 | test-row-30972 | 3.00 [3–3] | 3.00 [3–3] | 3.00 [3–3] |
| 250 | test-row-181614 | 4.00 [4–4] | 4.00 [4–4] | 4.00 [4–4] |
| 250 | test-row-155835 | 5.00 [5–5] | 4.00 [4–4] | 4.00 [4–4] |
| 250 | test-row-230080 | 2.00 [2–2] | 2.00 [2–2] | 2.00 [2–2] |
| 250 | test-row-200427 | 3.00 [3–3] | 3.00 [3–3] | 3.00 [3–3] |
| 250 | test-row-225258 | 3.00 [3–3] | 3.00 [3–3] | 3.00 [3–3] |
| 250 | test-row-237767 | 4.00 [4–4] | 3.00 [3–3] | 4.00 [4–4] |
| 250 | test-row-87149 | 4.00 [4–4] | 4.00 [4–4] | 4.00 [4–4] |
| 250 | test-row-232470 | 2.67 [2–3] | 3.00 [3–3] | 2.00 [2–2] |
| 250 | test-row-81274 | 3.00 [3–3] | 3.00 [3–3] | 3.00 [3–3] |
| 250 | test-row-105646 | 3.00 [3–3] | 3.00 [3–3] | 3.00 [3–3] |
| 250 | test-row-117849 | 3.00 [3–3] | 2.00 [2–2] | 3.00 [3–3] |
| 250 | test-row-9232 | 2.00 [2–2] | 3.00 [3–3] | 2.00 [2–2] |
| 250 | test-row-132289 | 2.00 [2–2] | 3.00 [3–3] | 3.00 [3–3] |
| 250 | test-row-136078 | 4.00 [4–4] | 3.00 [3–3] | 3.67 [3–4] |
| 1000 | test-row-102601 | 5.00 [5–5] | 5.00 [5–5] | 4.67 [4–5] |
| 1000 | test-row-30972 | 4.67 [4–5] | 3.67 [3–4] | 4.00 [4–4] |
| 1000 | test-row-181614 | 5.00 [5–5] | 5.00 [5–5] | 5.00 [5–5] |
| 1000 | test-row-155835 | 6.00 [6–6] | 5.00 [5–5] | 5.00 [5–5] |
| 1000 | test-row-230080 | 3.00 [3–3] | 3.00 [3–3] | 3.00 [3–3] |
| 1000 | test-row-200427 | 4.67 [4–5] | 4.00 [4–4] | 4.00 [4–4] |
| 1000 | test-row-225258 | 4.00 [4–4] | 4.00 [4–4] | 4.00 [4–4] |
| 1000 | test-row-237767 | 5.00 [5–5] | 4.00 [4–4] | 5.00 [5–5] |
| 1000 | test-row-87149 | 5.00 [5–5] | 5.00 [5–5] | 5.00 [5–5] |
| 1000 | test-row-232470 | 3.00 [3–3] | 4.00 [4–4] | 3.00 [3–3] |
| 1000 | test-row-81274 | 4.00 [4–4] | 4.00 [4–4] | 4.00 [4–4] |
| 1000 | test-row-105646 | 4.00 [4–4] | 4.00 [4–4] | 4.00 [4–4] |
| 1000 | test-row-117849 | 5.00 [5–5] | 3.00 [3–3] | 4.00 [4–4] |
| 1000 | test-row-9232 | 3.00 [3–3] | 4.00 [4–4] | 3.00 [3–3] |
| 1000 | test-row-132289 | 3.00 [3–3] | 4.00 [4–4] | 4.00 [4–4] |
| 1000 | test-row-136078 | 5.00 [5–5] | 5.00 [5–5] | 5.00 [5–5] |

## Interpretation

Hybrid static evaluation took 9.27x Classic's latency on this machine. The learned-evaluation path is therefore the clearest measured added cost and the next profiling target. This benchmark does not separate feature extraction from neural matrix operations, so it cannot identify which internal kernel dominates. See V2_OPTIMIZATION.md when comparing reference and optimized inference builds.

Search trees differ with evaluator scores: nodes/sec and completed depth measure the combined evaluator/search behavior, not inference cost alone. Nodes and TT hits include work in the last interrupted iteration; depth counts only completed iterations. TT clearing, position loading, warm-up and reporting are excluded from measured search times. Actual elapsed time is used for throughput, including budget overshoot and early mate exits. Static latency is batch-average wall time including feature extraction, clipping, and loop overhead; it is not a per-call latency percentile. CPU scheduling, clocks and load affect results. These timings are specific to this machine/build.

At 100 ms, Hybrid completed +0.104 plies versus Classic on average, with 0.829x its search nodes/sec.
At 250 ms, Hybrid completed -0.062 plies versus Classic on average, with 0.815x its search nodes/sec.
At 1000 ms, Hybrid completed -0.167 plies versus Classic on average, with 0.803x its search nodes/sec.
