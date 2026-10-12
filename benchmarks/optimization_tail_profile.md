# Hybrid V2 stage measurements

Model `v2-residual-3fb0a29e8514af8c`, alpha 0.25. Release, MSVC-19.28.29914.0.
CPU: AMD Ryzen 7 3700X 8-Core Processor. 16 fixed positions × 5 repetitions; at least 50,000 calls per stage/position/repetition.
Adaptive batches are retimed until at least 100.0 us; each row records its actual call count and duration. Discarded shorter attempts are not reported as measurements.
Warm-up: 2,000 calls before each batch. Bit-exact residual and integer Hybrid parity checked on 634 parents/legal children.

Batched reference-stage decomposition, with separate optimized kernel controls. Percentages use the freshly measured production call, not a normalized stage sum. Empty-call/loop overhead is subtracted once per independently timed stage. Small stages and fusion/cache differences limit attribution; stage percentages need not sum to 100%.

| Stage | Adjusted us/call | Raw us/call | % of production Hybrid | Across-batch std us |
|---|---:|---:|---:|---:|
| classic | 0.282042 | 0.283533 | 8.830% | 0.025571 |
| features | 0.476394 | 0.477885 | 14.914% | 0.043810 |
| linear1 | 3.381086 | 3.382578 | 105.849% | 0.326145 |
| relu1 | 0.066569 | 0.068061 | 2.084% | 0.005415 |
| linear2 | 4.988968 | 4.990459 | 156.186% | 0.133146 |
| relu2 | 0.034137 | 0.035629 | 1.069% | 0.005315 |
| output | 0.043453 | 0.044944 | 1.360% | 0.009192 |
| scale_add | 0.000244 | 0.001735 | 0.008% | 0.000371 |
| clip_round | 0.016210 | 0.017701 | 0.507% | 0.003282 |

Production total: **3.194243 us** adjusted; 3.195735 us raw.
Stage sum: 9.289103 us (290.81% of production). Signed attribution gap (production minus sum): -6.094859 us.
Empty call/loop control: 0.001491 us. Decomposed full pipeline: 9.577989 us.

## Controls (not additional additive production stages)

| Control | Adjusted us/call |
|---|---:|
| fused_tail_control | 5.081486 |
| linear1_no_skip_control | 54.776937 |
| base_features_control | 0.273836 |
| feature_copy_setup_control | 0.059824 |
| plane_counts_control | 0.353750 |
| optimized_tail_control | 0.835660 |
| optimized_linear1_control | 1.335366 |
| active_list_linear1_control | 0.971863 |

Removing zero-input skipping made the first layer 16.20x slower in the isolated control.

## Per-position adjusted microseconds

| Position | classic | features | linear1 | relu1 | linear2 | relu2 | output | scale_add | clip_round | Production |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| test-row-102601 | 0.2501 | 0.4720 | 3.0833 | 0.0659 | 5.0077 | 0.0337 | 0.0404 | 0.0006 | 0.0145 | 3.0476 |
| test-row-30972 | 0.2993 | 0.4798 | 3.4213 | 0.0662 | 4.9939 | 0.0338 | 0.0440 | 0.0005 | 0.0172 | 3.2798 |
| test-row-181614 | 0.3037 | 0.4828 | 3.6271 | 0.0678 | 4.9755 | 0.0319 | 0.0418 | 0.0002 | 0.0168 | 3.1955 |
| test-row-155835 | 0.2654 | 0.4776 | 3.0731 | 0.0709 | 5.0047 | 0.0378 | 0.0452 | 0.0004 | 0.0141 | 3.0618 |
| test-row-230080 | 0.2980 | 0.4561 | 3.7092 | 0.0646 | 4.9675 | 0.0373 | 0.0406 | 0.0003 | 0.0155 | 3.2782 |
| test-row-200427 | 0.2855 | 0.4755 | 3.5798 | 0.0645 | 5.1165 | 0.0315 | 0.0403 | 0.0000 | 0.0172 | 3.3549 |
| test-row-225258 | 0.2742 | 0.4765 | 3.4800 | 0.0734 | 4.9971 | 0.0325 | 0.0431 | 0.0002 | 0.0175 | 3.2206 |
| test-row-237767 | 0.2617 | 0.4660 | 3.0059 | 0.0641 | 4.9550 | 0.0360 | 0.0450 | 0.0005 | 0.0142 | 3.0738 |
| test-row-87149 | 0.3130 | 0.5061 | 3.5475 | 0.0635 | 4.9508 | 0.0346 | 0.0453 | 0.0000 | 0.0166 | 3.3083 |
| test-row-232470 | 0.2965 | 0.4808 | 3.5719 | 0.0676 | 4.9539 | 0.0325 | 0.0386 | 0.0002 | 0.0136 | 3.3036 |
| test-row-81274 | 0.3049 | 0.5009 | 3.8819 | 0.0683 | 5.0075 | 0.0359 | 0.0520 | 0.0001 | 0.0207 | 3.3677 |
| test-row-105646 | 0.2865 | 0.4759 | 3.1560 | 0.0655 | 4.9471 | 0.0334 | 0.0406 | 0.0000 | 0.0155 | 3.1593 |
| test-row-117849 | 0.2968 | 0.4820 | 3.2868 | 0.0671 | 4.9449 | 0.0325 | 0.0414 | 0.0001 | 0.0159 | 3.1370 |
| test-row-9232 | 0.2844 | 0.4906 | 3.7943 | 0.0656 | 5.0729 | 0.0370 | 0.0534 | 0.0003 | 0.0190 | 3.2664 |
| test-row-132289 | 0.2362 | 0.4392 | 3.0351 | 0.0654 | 4.9644 | 0.0339 | 0.0453 | 0.0002 | 0.0157 | 3.1227 |
| test-row-136078 | 0.2565 | 0.4605 | 2.8442 | 0.0649 | 4.9642 | 0.0318 | 0.0382 | 0.0002 | 0.0155 | 2.9307 |

Per-position percentages, batch variability, controls, sparsity and every raw measurement are retained in the JSON. See V2_OPTIMIZATION.md for implementation, compiler evidence and parity results.
