# Measured evaluator performance

Performance only; these are not playing-strength results.

Machine: AMD Ryzen 7 3700X 8-Core Processor; Windows-10-10.0.19045-SP0. Build: Release, MSVC-19.28.29914.0.
Hybrid alpha: 0.25; model: `v2-residual-3fb0a29e8514af8c`.
Manifest: `performance-middlegames-v1`, SHA-256 `da829c823df87a0aa6f8cbf436093b4a526019c8ec68111cea8fe28e1573e9c7`.
16 positions, 3 repetitions; one search thread. UTC: 2026-09-25T01:35:25.232928+00:00.

## Static evaluation

| Evaluator | Evaluations/sec | Average latency us | Batch latency std us | Slowdown |
|---|---:|---:|---:|---:|
| classic | 2,314,045 | 0.432 | 0.016 | 1.00x |
| ml | 109,734 | 9.113 | 0.456 | 21.09x |
| hybrid | 105,100 | 9.515 | 0.093 | 22.02x |

## Search at equal wall-clock budgets

| Budget ms | Evaluator | Avg completed depth | Depth delta vs Classic | Avg nodes | Nodes/sec | Total nodes | TT hits | Elapsed s |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 100 | classic | 2.396 | +0.000 | 9,222 | 92,205 | 442,635 | 3,778 | 4.801 |
| 100 | ml | 2.500 | +0.104 | 6,264 | 62,564 | 300,677 | 2,348 | 4.806 |
| 100 | hybrid | 2.167 | -0.229 | 5,959 | 59,491 | 286,014 | 1,893 | 4.808 |
| 250 | classic | 2.979 | +0.000 | 23,352 | 93,391 | 1,120,911 | 11,316 | 12.002 |
| 250 | ml | 3.104 | +0.125 | 15,956 | 63,808 | 765,911 | 9,615 | 12.003 |
| 250 | hybrid | 2.938 | -0.042 | 15,519 | 62,057 | 744,906 | 8,965 | 12.004 |
| 1000 | classic | 4.062 | +0.000 | 95,704 | 95,702 | 4,593,777 | 60,328 | 48.001 |
| 1000 | ml | 3.875 | -0.188 | 65,104 | 65,100 | 3,125,007 | 48,717 | 48.003 |
| 1000 | hybrid | 3.854 | -0.208 | 61,991 | 61,986 | 2,975,574 | 37,226 | 48.004 |

## Per-position completed depths

Each cell: mean [min–max] across repetitions. Raw nodes, elapsed time, TT hits and moves are in JSON.

| Budget ms | Position | Classic | ML | Hybrid |
|---|---|---:|---:|---:|
| 100 | test-row-102601 | 3.00 [3–3] | 3.00 [3–3] | 2.00 [2–2] |
| 100 | test-row-30972 | 3.00 [3–3] | 2.00 [2–2] | 2.67 [2–3] |
| 100 | test-row-181614 | 3.00 [3–3] | 3.00 [3–3] | 3.00 [3–3] |
| 100 | test-row-155835 | 4.00 [4–4] | 3.00 [3–3] | 3.67 [3–4] |
| 100 | test-row-230080 | 0.00 [0–0] | 1.00 [1–1] | 0.00 [0–0] |
| 100 | test-row-200427 | 3.00 [3–3] | 3.00 [3–3] | 2.67 [2–3] |
| 100 | test-row-225258 | 2.00 [2–2] | 2.00 [2–2] | 2.00 [2–2] |
| 100 | test-row-237767 | 3.00 [3–3] | 3.00 [3–3] | 3.00 [3–3] |
| 100 | test-row-87149 | 3.00 [3–3] | 3.00 [3–3] | 3.00 [3–3] |
| 100 | test-row-232470 | 1.33 [1–2] | 3.00 [3–3] | 1.00 [1–1] |
| 100 | test-row-81274 | 2.00 [2–2] | 3.00 [3–3] | 1.67 [1–2] |
| 100 | test-row-105646 | 3.00 [3–3] | 2.00 [2–2] | 2.00 [2–2] |
| 100 | test-row-117849 | 3.00 [3–3] | 2.00 [2–2] | 3.00 [3–3] |
| 100 | test-row-9232 | 1.00 [1–1] | 2.00 [2–2] | 1.00 [1–1] |
| 100 | test-row-132289 | 1.00 [1–1] | 2.00 [2–2] | 1.00 [1–1] |
| 100 | test-row-136078 | 3.00 [3–3] | 3.00 [3–3] | 3.00 [3–3] |
| 250 | test-row-102601 | 3.67 [3–4] | 4.00 [4–4] | 3.00 [3–3] |
| 250 | test-row-30972 | 3.00 [3–3] | 2.67 [2–3] | 3.00 [3–3] |
| 250 | test-row-181614 | 4.00 [4–4] | 4.00 [4–4] | 4.00 [4–4] |
| 250 | test-row-155835 | 4.00 [4–4] | 4.00 [4–4] | 4.00 [4–4] |
| 250 | test-row-230080 | 2.00 [2–2] | 2.00 [2–2] | 2.00 [2–2] |
| 250 | test-row-200427 | 3.00 [3–3] | 3.00 [3–3] | 3.00 [3–3] |
| 250 | test-row-225258 | 3.00 [3–3] | 3.00 [3–3] | 3.00 [3–3] |
| 250 | test-row-237767 | 3.00 [3–3] | 3.00 [3–3] | 4.00 [4–4] |
| 250 | test-row-87149 | 4.00 [4–4] | 4.00 [4–4] | 4.00 [4–4] |
| 250 | test-row-232470 | 2.00 [2–2] | 3.00 [3–3] | 2.00 [2–2] |
| 250 | test-row-81274 | 3.00 [3–3] | 3.00 [3–3] | 3.00 [3–3] |
| 250 | test-row-105646 | 3.00 [3–3] | 3.00 [3–3] | 3.00 [3–3] |
| 250 | test-row-117849 | 3.00 [3–3] | 2.00 [2–2] | 3.00 [3–3] |
| 250 | test-row-9232 | 2.00 [2–2] | 3.00 [3–3] | 1.00 [1–1] |
| 250 | test-row-132289 | 2.00 [2–2] | 3.00 [3–3] | 2.00 [2–2] |
| 250 | test-row-136078 | 3.00 [3–3] | 3.00 [3–3] | 3.00 [3–3] |
| 1000 | test-row-102601 | 4.00 [4–4] | 5.00 [5–5] | 4.00 [4–4] |
| 1000 | test-row-30972 | 4.00 [4–4] | 3.00 [3–3] | 4.00 [4–4] |
| 1000 | test-row-181614 | 5.00 [5–5] | 4.00 [4–4] | 4.00 [4–4] |
| 1000 | test-row-155835 | 6.00 [6–6] | 5.00 [5–5] | 5.00 [5–5] |
| 1000 | test-row-230080 | 3.00 [3–3] | 3.00 [3–3] | 3.00 [3–3] |
| 1000 | test-row-200427 | 4.00 [4–4] | 4.00 [4–4] | 4.00 [4–4] |
| 1000 | test-row-225258 | 4.00 [4–4] | 4.00 [4–4] | 4.00 [4–4] |
| 1000 | test-row-237767 | 4.00 [4–4] | 4.00 [4–4] | 4.00 [4–4] |
| 1000 | test-row-87149 | 5.00 [5–5] | 5.00 [5–5] | 5.00 [5–5] |
| 1000 | test-row-232470 | 3.00 [3–3] | 3.00 [3–3] | 3.00 [3–3] |
| 1000 | test-row-81274 | 4.00 [4–4] | 4.00 [4–4] | 3.00 [3–3] |
| 1000 | test-row-105646 | 4.00 [4–4] | 4.00 [4–4] | 4.00 [4–4] |
| 1000 | test-row-117849 | 4.00 [4–4] | 3.00 [3–3] | 3.67 [3–4] |
| 1000 | test-row-9232 | 3.00 [3–3] | 3.00 [3–3] | 3.00 [3–3] |
| 1000 | test-row-132289 | 3.00 [3–3] | 4.00 [4–4] | 3.00 [3–3] |
| 1000 | test-row-136078 | 5.00 [5–5] | 4.00 [4–4] | 5.00 [5–5] |

## Interpretation

Hybrid static evaluation took 22.02x Classic's latency on this machine. The learned-evaluation path is therefore the clearest measured added cost and the next profiling target. This benchmark does not separate feature extraction from neural matrix operations, so it cannot identify which internal kernel dominates. No inference optimization was performed.

Search trees differ with evaluator scores: nodes/sec and completed depth measure the combined evaluator/search behavior, not inference cost alone. Nodes and TT hits include work in the last interrupted iteration; depth counts only completed iterations. TT clearing, position loading, warm-up and reporting are excluded from measured search times. Actual elapsed time is used for throughput, including budget overshoot and early mate exits. Static latency is batch-average wall time including feature extraction, clipping, and loop overhead; it is not a per-call latency percentile. CPU scheduling, clocks and load affect results. These timings are specific to this machine/build.

At 100 ms, Hybrid completed -0.229 plies versus Classic on average, with 0.645x its search nodes/sec.
At 250 ms, Hybrid completed -0.042 plies versus Classic on average, with 0.664x its search nodes/sec.
At 1000 ms, Hybrid completed -0.208 plies versus Classic on average, with 0.648x its search nodes/sec.
