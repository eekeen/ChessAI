# Hybrid V2 stage measurements

Model `v2-residual-3fb0a29e8514af8c`, alpha 0.25. Release, MSVC-19.28.29914.0.
CPU: AMD Ryzen 7 3700X 8-Core Processor. 16 fixed positions × 5 repetitions; at least 50,000 calls per stage/position/repetition.
Adaptive batches are retimed until at least 100.0 us; each row records its actual call count and duration. Discarded shorter attempts are not reported as measurements.
Warm-up: 2,000 calls before each batch. Bit-exact residual and integer Hybrid parity checked on 634 parents/legal children.

Batched, profiling-only stage decomposition; the production fused tail is unchanged. Percentages use the freshly measured production call, not a normalized stage sum. Empty-call/loop overhead is subtracted once per independently timed stage. Small stages and fusion/cache differences limit attribution; stage percentages need not sum to 100%.

| Stage | Adjusted us/call | Raw us/call | % of production Hybrid | Across-batch std us |
|---|---:|---:|---:|---:|
| classic | 0.293129 | 0.294997 | 3.363% | 0.051686 |
| features | 0.548096 | 0.549964 | 6.288% | 0.057340 |
| linear1 | 4.268629 | 4.270498 | 48.972% | 0.395490 |
| relu1 | 0.075106 | 0.076975 | 0.862% | 0.014709 |
| linear2 | 5.476879 | 5.478747 | 62.834% | 0.323975 |
| relu2 | 0.037214 | 0.039083 | 0.427% | 0.007066 |
| output | 0.053376 | 0.055244 | 0.612% | 0.016917 |
| scale_add | 0.000076 | 0.001944 | 0.001% | 0.000439 |
| clip_round | 0.019592 | 0.021460 | 0.225% | 0.007871 |

Production total: **8.716450 us** adjusted; 8.718319 us raw.
Stage sum: 10.772095 us (123.58% of production). Signed attribution gap (production minus sum): -2.055645 us.
Empty call/loop control: 0.001869 us. Decomposed full pipeline: 11.167699 us.

## Controls (not additional additive production stages)

| Control | Adjusted us/call |
|---|---:|
| fused_tail_control | 5.554750 |
| linear1_no_skip_control | 60.998846 |
| base_features_control | 0.291248 |
| feature_copy_setup_control | 0.069769 |
| plane_counts_control | 0.397347 |

Removing zero-input skipping made the first layer 14.29x slower in the isolated control.

## Per-position adjusted microseconds

| Position | classic | features | linear1 | relu1 | linear2 | relu2 | output | scale_add | clip_round | Production |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| test-row-102601 | 0.2504 | 0.5362 | 3.9303 | 0.0763 | 5.6216 | 0.0385 | 0.0495 | 0.0006 | 0.0201 | 8.7419 |
| test-row-30972 | 0.3156 | 0.5302 | 4.1208 | 0.0730 | 5.4952 | 0.0357 | 0.0551 | 0.0004 | 0.0197 | 9.3779 |
| test-row-181614 | 0.3565 | 0.5522 | 4.3519 | 0.0761 | 5.2679 | 0.0358 | 0.0505 | 0.0004 | 0.0186 | 8.3838 |
| test-row-155835 | 0.2725 | 0.5685 | 3.8058 | 0.0703 | 5.3609 | 0.0383 | 0.0435 | -0.0000 | 0.0175 | 8.1742 |
| test-row-230080 | 0.2704 | 0.5251 | 4.5267 | 0.0874 | 5.4163 | 0.0338 | 0.0442 | 0.0005 | 0.0166 | 8.9361 |
| test-row-200427 | 0.2941 | 0.5295 | 4.4889 | 0.0704 | 5.3942 | 0.0396 | 0.0557 | 0.0008 | 0.0171 | 8.7399 |
| test-row-225258 | 0.2798 | 0.5410 | 4.4160 | 0.0703 | 5.5725 | 0.0406 | 0.0545 | 0.0002 | 0.0327 | 8.4653 |
| test-row-237767 | 0.2655 | 0.5620 | 3.9105 | 0.0714 | 5.2996 | 0.0372 | 0.0492 | 0.0006 | 0.0190 | 8.5852 |
| test-row-87149 | 0.3301 | 0.5560 | 4.4777 | 0.0783 | 5.6900 | 0.0365 | 0.0573 | 0.0003 | 0.0186 | 8.6882 |
| test-row-232470 | 0.2924 | 0.5636 | 4.6115 | 0.0623 | 5.4964 | 0.0299 | 0.0484 | -0.0066 | 0.0135 | 9.3130 |
| test-row-81274 | 0.3220 | 0.5888 | 4.9644 | 0.0742 | 5.4628 | 0.0373 | 0.0491 | 0.0007 | 0.0213 | 9.0714 |
| test-row-105646 | 0.2883 | 0.5663 | 4.0475 | 0.0766 | 5.5822 | 0.0428 | 0.0625 | 0.0006 | 0.0214 | 8.6342 |
| test-row-117849 | 0.3207 | 0.5324 | 4.2262 | 0.0710 | 5.4387 | 0.0379 | 0.0599 | 0.0006 | 0.0196 | 8.4612 |
| test-row-9232 | 0.2936 | 0.5229 | 4.6325 | 0.0874 | 5.3153 | 0.0338 | 0.0661 | 0.0007 | 0.0242 | 9.0799 |
| test-row-132289 | 0.2833 | 0.5699 | 4.0620 | 0.0819 | 5.7664 | 0.0415 | 0.0567 | 0.0011 | 0.0179 | 8.4820 |
| test-row-136078 | 0.2549 | 0.5250 | 3.7253 | 0.0748 | 5.4502 | 0.0362 | 0.0519 | 0.0005 | 0.0158 | 8.3289 |

Per-position percentages, batch variability, controls, sparsity and every raw measurement are retained in the JSON. See HYBRID_PROFILE.md for compiler evidence, limitations and optimization recommendations. No production optimization was applied.
