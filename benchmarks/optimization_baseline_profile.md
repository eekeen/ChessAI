# Hybrid V2 stage measurements

Model `v2-residual-3fb0a29e8514af8c`, alpha 0.25. Release, MSVC-19.28.29914.0.
CPU: AMD Ryzen 7 3700X 8-Core Processor. 16 fixed positions × 5 repetitions; at least 50,000 calls per stage/position/repetition.
Adaptive batches are retimed until at least 100.0 us; each row records its actual call count and duration. Discarded shorter attempts are not reported as measurements.
Warm-up: 2,000 calls before each batch. Bit-exact residual and integer Hybrid parity checked on 634 parents/legal children.

Batched, profiling-only stage decomposition; the production fused tail is unchanged. Percentages use the freshly measured production call, not a normalized stage sum. Empty-call/loop overhead is subtracted once per independently timed stage. Small stages and fusion/cache differences limit attribution; stage percentages need not sum to 100%.

| Stage | Adjusted us/call | Raw us/call | % of production Hybrid | Across-batch std us |
|---|---:|---:|---:|---:|
| classic | 0.262884 | 0.264272 | 3.476% | 0.035356 |
| features | 0.464641 | 0.466029 | 6.144% | 0.067793 |
| linear1 | 3.755671 | 3.757058 | 49.662% | 0.463014 |
| relu1 | 0.066315 | 0.067702 | 0.877% | 0.004957 |
| linear2 | 5.093708 | 5.095096 | 67.355% | 0.611283 |
| relu2 | 0.033149 | 0.034537 | 0.438% | 0.003517 |
| output | 0.043114 | 0.044501 | 0.570% | 0.010456 |
| scale_add | 0.000411 | 0.001798 | 0.005% | 0.000723 |
| clip_round | 0.016730 | 0.018118 | 0.221% | 0.004892 |

Production total: **7.562527 us** adjusted; 7.563915 us raw.
Stage sum: 9.736624 us (128.75% of production). Signed attribution gap (production minus sum): -2.174097 us.
Empty call/loop control: 0.001387 us. Decomposed full pipeline: 9.992957 us.

## Controls (not additional additive production stages)

| Control | Adjusted us/call |
|---|---:|
| fused_tail_control | 5.166407 |
| linear1_no_skip_control | 55.347772 |
| base_features_control | 0.245558 |
| feature_copy_setup_control | 0.060106 |
| plane_counts_control | 0.351439 |

Removing zero-input skipping made the first layer 14.74x slower in the isolated control.

## Per-position adjusted microseconds

| Position | classic | features | linear1 | relu1 | linear2 | relu2 | output | scale_add | clip_round | Production |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| test-row-102601 | 0.2315 | 0.4894 | 3.6753 | 0.0706 | 5.1606 | 0.0341 | 0.0427 | 0.0003 | 0.0157 | 7.5440 |
| test-row-30972 | 0.2956 | 0.4899 | 3.8172 | 0.0648 | 5.0157 | 0.0324 | 0.0428 | 0.0004 | 0.0141 | 7.4133 |
| test-row-181614 | 0.2795 | 0.4593 | 3.9270 | 0.0663 | 5.0694 | 0.0326 | 0.0435 | 0.0003 | 0.0178 | 7.7091 |
| test-row-155835 | 0.2524 | 0.4614 | 3.4512 | 0.0653 | 5.0506 | 0.0326 | 0.0405 | 0.0001 | 0.0142 | 7.3514 |
| test-row-230080 | 0.2492 | 0.4774 | 4.1340 | 0.0653 | 5.1150 | 0.0333 | 0.0446 | 0.0003 | 0.0157 | 7.7681 |
| test-row-200427 | 0.2561 | 0.4773 | 4.1369 | 0.0665 | 5.9601 | 0.0324 | 0.0556 | 0.0001 | 0.0177 | 8.0471 |
| test-row-225258 | 0.2631 | 0.4889 | 3.8946 | 0.0674 | 5.0944 | 0.0315 | 0.0391 | 0.0006 | 0.0223 | 7.9752 |
| test-row-237767 | 0.2637 | 0.4725 | 3.5032 | 0.0670 | 5.0636 | 0.0378 | 0.0489 | 0.0017 | 0.0192 | 7.5734 |
| test-row-87149 | 0.3321 | 0.5092 | 4.0392 | 0.0674 | 5.0360 | 0.0328 | 0.0450 | 0.0005 | 0.0163 | 7.5617 |
| test-row-232470 | 0.2601 | 0.4386 | 3.7909 | 0.0682 | 4.9295 | 0.0312 | 0.0387 | 0.0002 | 0.0137 | 8.0727 |
| test-row-81274 | 0.2695 | 0.4488 | 4.1958 | 0.0688 | 5.0717 | 0.0318 | 0.0418 | 0.0001 | 0.0165 | 7.5451 |
| test-row-105646 | 0.2640 | 0.4338 | 3.4451 | 0.0646 | 5.0405 | 0.0340 | 0.0421 | 0.0002 | 0.0174 | 7.2272 |
| test-row-117849 | 0.2534 | 0.4280 | 3.4882 | 0.0649 | 4.9165 | 0.0343 | 0.0372 | 0.0002 | 0.0168 | 7.1598 |
| test-row-9232 | 0.2457 | 0.4348 | 3.9566 | 0.0646 | 4.9457 | 0.0336 | 0.0415 | 0.0006 | 0.0186 | 7.4807 |
| test-row-132289 | 0.2564 | 0.4819 | 3.4525 | 0.0638 | 5.0304 | 0.0329 | 0.0452 | 0.0006 | 0.0152 | 7.2849 |
| test-row-136078 | 0.2340 | 0.4432 | 3.1831 | 0.0656 | 4.9997 | 0.0331 | 0.0407 | 0.0003 | 0.0163 | 7.2868 |

Per-position percentages, batch variability, controls, sparsity and every raw measurement are retained in the JSON. See HYBRID_PROFILE.md for compiler evidence, limitations and optimization recommendations. No production optimization was applied.
