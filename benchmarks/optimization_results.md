# Measured V2 inference optimization

Model `v2-residual-3fb0a29e8514af8c`, alpha **0.25**. Ryzen 7 3700X, MSVC 19.28, Release.
Selected production implementation: **AVX2 fused tail + active-index sparse Linear1**.

Fresh reference profile: 7.562527 us/evaluation. Final production: **3.031207 us/evaluation**, **2.495x throughput**, **59.92% less latency**.

## Same-run candidate comparison

All complete candidates rotated within the same run: 16 positions, five repetitions, 50,000 calls and 2,000 warm-up calls. Totals include features, Classic, residual scaling, clipping and rounding. Explicit-backend wrappers omit only mode dispatch. Eval/s is the reciprocal of adjusted latency. Speedup below means latency reduction versus the requested fresh reference baseline.

| Implementation | Hybrid us/eval | eval/s | Linear1 us | Tail us | Speedup vs fresh reference |
|---|---:|---:|---:|---:|---:|
| Reference (shared run) | 7.847 | 127,431 | 3.556 | 5.205 | -3.77% |
| Tail only | 3.314 | 301,739 | 3.556 | 0.863 | +56.18% |
| AVX2 scan Linear1 only | 8.510 | 117,507 | 1.912 | 5.205 | -12.53% |
| Active-list Linear1 only | 7.617 | 131,288 | 1.032 | 5.205 | -0.72% |
| Tail + AVX2 scan Linear1 | 3.918 | 255,202 | 1.912 | 0.863 | +48.19% |
| Tail + active-list Linear1 | 3.172 | 315,265 | 1.032 | 0.863 | +58.06% |

The same-run reference measured 7.847 us versus the earlier 7.563 us, showing run-to-run variation. Candidate ranking uses same-run comparisons and the alternating production-entry check below. The reference Linear1 control is an isolated scalar profiling copy; original production Linear1 receives SSE code generation. Do not sum isolated stage controls or mistake their ratio for end-to-end acceleration.

Common controls in this run: features **0.642409 us**; reference Linear1 **3.555558 us**; AVX2 scan Linear1 **1.912022 us**; active-list Linear1 **1.031897 us**; reference tail **5.205243 us**; optimized tail **0.863451 us**.
Isolated active-list construction: **0.603634 us**. Construction is already included in active-list kernel and total timings; it is not subtracted or added again. Feature extraction is unchanged for every candidate. Average active features: **38.375 / 789**.

The AVX2 scan is rejected: it loses end-to-end to the existing SSE path. Active-list-only is not deployed; its small gain against the same-run reference does not beat the earlier fresh baseline. Only the combined tail/active-list winner is selected.

## Production-entry confirmation

Alternating tail/active/active/tail runs measured 3.729205, 3.045241, 3.086013, 3.572951 us respectively. Tail mean **3.651078 us**; active-list mean **3.065627 us**: **16.04% less latency** including construction and actual production dispatch. Each run used the same 16 round-robin positions, three 200,000-evaluation repetitions and 10,000 warm-up evaluations. The 1 ms search smoke accompanying these static runs is not used to select an implementation.

## Final production versus fresh reference

| Measurement | Reference | Tail only | Selected production |
|---|---:|---:|---:|
| Profile Hybrid us | 7.562527 | 3.194243 | 3.031207 |
| Feature extraction us | 0.464641 | 0.476394 | 0.608443 |
| Selected Linear1 control us | 3.755671 | 3.381086 | 0.986080 |
| Selected tail control us | 5.166407 | 0.835660 | 0.844846 |

Round-robin production benchmark: **8.120015 → 3.129293 us**, **123,152 → 319,561 eval/s** (159.48% higher throughput; 61.46% lower latency). These round-robin timings have different cache behavior from repeated-position profiling.

## Search, unchanged settings

| Budget | Nodes/s before → after | Improvement | Mean completed depth before → after | Total nodes before → after |
|---|---:|---:|---:|---:|
| 100 ms | 63,385 → 88,130 | +39.04% | 2.208 → 2.625 | 304,415 → 423,160 |
| 250 ms | 67,080 → 85,610 | +27.62% | 2.938 → 3.062 | 805,176 → 1,027,465 |
| 1000 ms | 67,415 → 87,237 | +29.40% | 4.000 → 4.125 | 3,236,151 → 4,187,709 |

Three repetitions on all 16 positions at each budget, identical search code/settings and cleared TT. Timed depth is a performance observation, not strength evidence.

Run-to-run conditions matter: the earlier tail-only run also had faster unchanged Classic searches
(124,936 nodes/s at 1000 ms, versus 105,869 in the final run and 105,210 in the fresh baseline).
Therefore the separate tail/final search runs do not establish the active-list component's incremental
search gain. Selection uses the same-run complete-evaluator comparison and alternating production
static check; the table reports the requested final-versus-fresh-reference search measurements.

## Correctness and attribution

**250,000/250,000 production residuals bit-identical; max/mean difference 0 cp; zero rounded Hybrid score changes.** All explicit candidates also pass. Python/C++ parity, profiler parity, native perft/evaluation/search/game-rule/tournament/opening tests, tournament overrides, frozen manifests, protocol, diagnostics, GUI defaults and ML pipeline tests pass.

All **25 protected artifacts** retain their original hashes. The original `forward` implementation
and feature extraction body are textually unchanged. At fixed depth 3, all **48 search cases**
(16 performance positions × three evaluators, alpha 0.25) return identical scores, moves and node
counts versus the reference fallback. Evidence: `optimization_integrity.json`.

The AVX2-disabled fallback build passes all 250,000 positions, profiler parity and all four native test groups. Runtime CPU/OS checks preserve this reference path on unsupported CPUs. A physical non-AVX2 CPU was not available.

The **fused tail is the largest contributor**: tail-only reduced the fresh profile from 7.563 to 3.194 us. Active-index Linear1 supplies the smaller additional measured gain. No features, weights, alpha, search settings or frozen strength suites/results changed. No final strength matches ran.

Implementation, compiler flags, exact commands and validation details: [V2_OPTIMIZATION.md](V2_OPTIMIZATION.md). Raw per-position/per-repetition measurements are preserved in the matching `optimization_*.json` reports.
