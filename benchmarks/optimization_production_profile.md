# Hybrid V2 stage measurements

Model `v2-residual-3fb0a29e8514af8c`, alpha 0.25. Release, MSVC-19.28.29914.0.
CPU: AMD Ryzen 7 3700X 8-Core Processor. 16 fixed positions × 5 repetitions; at least 50,000 calls per stage/position/repetition.
Adaptive batches are retimed until at least 100.0 us; each row records its actual call count and duration. Discarded shorter attempts are not reported as measurements.
Warm-up: 2,000 calls before each batch. Bit-exact residual and integer Hybrid parity checked on 634 parents/legal children.

Batched reference-stage decomposition, with separate optimized kernel controls. Percentages use the freshly measured production call, not a normalized stage sum. Empty-call/loop overhead is subtracted once per independently timed stage. Small stages and fusion/cache differences limit attribution; stage percentages need not sum to 100%.

| Stage | Adjusted us/call | Raw us/call | % of production Hybrid | Across-batch std us |
|---|---:|---:|---:|---:|
| classic | 0.274923 | 0.276366 | 9.070% | 0.043887 |
| features | 0.608443 | 0.609886 | 20.073% | 0.075340 |
| linear1 | 3.530927 | 3.532369 | 116.486% | 0.363290 |
| relu1 | 0.069941 | 0.071383 | 2.307% | 0.007453 |
| linear2 | 5.094185 | 5.095627 | 168.058% | 0.134320 |
| relu2 | 0.033616 | 0.035059 | 1.109% | 0.003092 |
| output | 0.044826 | 0.046268 | 1.479% | 0.008057 |
| scale_add | 0.000429 | 0.001871 | 0.014% | 0.000487 |
| clip_round | 0.017115 | 0.018558 | 0.565% | 0.003321 |

Production total: **3.031207 us** adjusted; 3.032650 us raw.
Stage sum: 9.674404 us (319.16% of production). Signed attribution gap (production minus sum): -6.643197 us.
Empty call/loop control: 0.001443 us. Decomposed full pipeline: 9.989406 us.

## Controls (not additional additive production stages)

| Control | Adjusted us/call |
|---|---:|
| fused_tail_control | 5.163041 |
| linear1_no_skip_control | 56.104515 |
| base_features_control | 0.374226 |
| feature_copy_setup_control | 0.061021 |
| plane_counts_control | 0.358066 |
| optimized_tail_control | 0.844846 |
| optimized_linear1_control | 1.770207 |
| active_list_linear1_control | 0.986080 |

Removing zero-input skipping made the first layer 15.89x slower in the isolated control.

## Per-position adjusted microseconds

| Position | classic | features | linear1 | relu1 | linear2 | relu2 | output | scale_add | clip_round | Production |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| test-row-102601 | 0.2361 | 0.5592 | 3.2541 | 0.0711 | 5.1117 | 0.0335 | 0.0376 | 0.0004 | 0.0144 | 2.8422 |
| test-row-30972 | 0.2878 | 0.5792 | 3.4220 | 0.0705 | 5.0602 | 0.0355 | 0.0383 | 0.0002 | 0.0162 | 2.9308 |
| test-row-181614 | 0.2939 | 0.6228 | 3.7038 | 0.0687 | 5.0850 | 0.0339 | 0.0434 | 0.0011 | 0.0182 | 3.0865 |
| test-row-155835 | 0.2401 | 0.5918 | 3.1586 | 0.0675 | 5.0121 | 0.0342 | 0.0429 | 0.0003 | 0.0149 | 2.8487 |
| test-row-230080 | 0.2921 | 0.7244 | 3.9647 | 0.0739 | 5.1482 | 0.0342 | 0.0488 | 0.0002 | 0.0167 | 3.0486 |
| test-row-200427 | 0.2703 | 0.6119 | 3.7703 | 0.0654 | 5.1453 | 0.0334 | 0.0501 | 0.0005 | 0.0181 | 3.0365 |
| test-row-225258 | 0.2652 | 0.5949 | 3.5538 | 0.0729 | 5.1068 | 0.0367 | 0.0513 | 0.0004 | 0.0214 | 3.4245 |
| test-row-237767 | 0.2602 | 0.6050 | 3.2070 | 0.0722 | 5.1403 | 0.0333 | 0.0504 | 0.0007 | 0.0172 | 3.0121 |
| test-row-87149 | 0.3053 | 0.5921 | 3.5862 | 0.0686 | 5.0086 | 0.0317 | 0.0409 | 0.0002 | 0.0177 | 3.4488 |
| test-row-232470 | 0.3572 | 0.6171 | 3.6527 | 0.0704 | 5.0902 | 0.0336 | 0.0423 | 0.0002 | 0.0147 | 3.0075 |
| test-row-81274 | 0.2884 | 0.6115 | 4.0882 | 0.0666 | 5.0646 | 0.0328 | 0.0439 | 0.0007 | 0.0199 | 3.0852 |
| test-row-105646 | 0.2625 | 0.5705 | 3.2587 | 0.0713 | 5.0453 | 0.0330 | 0.0410 | 0.0003 | 0.0165 | 2.9421 |
| test-row-117849 | 0.2800 | 0.6016 | 3.5638 | 0.0720 | 5.0932 | 0.0326 | 0.0443 | 0.0001 | 0.0190 | 2.9766 |
| test-row-9232 | 0.2712 | 0.6538 | 3.9809 | 0.0691 | 5.1528 | 0.0331 | 0.0468 | 0.0007 | 0.0185 | 2.9336 |
| test-row-132289 | 0.2337 | 0.6223 | 3.1664 | 0.0706 | 5.0793 | 0.0327 | 0.0473 | 0.0005 | 0.0150 | 2.9377 |
| test-row-136078 | 0.2548 | 0.5768 | 3.1637 | 0.0684 | 5.1634 | 0.0337 | 0.0477 | 0.0005 | 0.0153 | 2.9379 |

Per-position percentages, batch variability, controls, sparsity and every raw measurement are retained in the JSON. See V2_OPTIMIZATION.md for implementation, compiler evidence and parity results.
