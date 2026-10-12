# Frozen V2 evaluator diagnostics

The frozen neural models fit clipped held-out Stockfish labels better than Classic, while the supplied depth-3 paired matches favor Classic. These are different measurements. Correction magnitudes, local changes and clipping are diagnostic observations, not proof of the cause. Sibling ranking is unavailable without complete trusted child labels.

No training or model changes. All scores are White centipawns. Percentages use 0–100; ranking accuracy uses 0–1.

## A. Global held-out label error

Full test split; labels are already clipped at ±1500. Raw and deployed scores are reported separately.

| Evaluator | MAE cp | RMSE cp |
|---|---:|---:|
| classic | 452.93 | 655.27 |
| ml | 256.58 | 443.74 |
| hybrid | 251.39 | 438.10 |
| direct_raw | 258.67 | 444.52 |
| hybrid_raw | 256.91 | 439.80 |

## B. Sibling move ranking

With --stockfish, every child uses that engine at identical depth (no mixed label sources). Otherwise only complete local cached sets are ranked. Cached FEN matching uses the first four fields, retains en-passant, ignores clocks/history; coverage is conservative. Parents with any mate score or missing label are excluded from cp ranking/regret; mates are never mapped to invented centipawns.

Parents sampled: 500; complete nonterminal cp-labelled sets: 0; cached child labels: 86 / 14141; mate-containing sets excluded: 0; forced-move parents excluded: 1.

**Ranking unavailable:** no complete, trusted child-label sets. Pass `--stockfish` to measure it; no labels were invented.

Top-1 accepts any target-best tie. Top-3 means at least one target-best child is among the evaluator's first three. UCI move order breaks prediction ties; JSON also reports uniform tie expectations. Pairwise excludes target ties, credits predicted ties 0.5, and averages per parent. Spearman uses average ranks, excluding constant rankings. All metrics optimize for the parent side; regret is nonnegative.

## C. Parent–child stability

Deltas are child minus parent in White cp. Captures can legitimately change material; this is not an accuracy metric.

| Evaluator/group | Edges | Median abs | p90 abs | p95 abs | p99 abs | Sign flips % | >300 cp % |
|---|---:|---:|---:|---:|---:|---:|---:|
| classic/capture | 934 | 120.00 | 345.00 | 495.00 | 903.35 | 33.19 | 28.91 |
| classic/quiet | 13207 | 5.00 | 20.00 | 35.00 | 50.00 | 1.82 | 0.11 |
| ml/capture | 934 | 91.00 | 332.70 | 485.90 | 770.01 | 12.74 | 11.46 |
| ml/quiet | 13207 | 95.00 | 295.00 | 435.70 | 810.00 | 17.25 | 9.70 |
| hybrid/capture | 934 | 99.50 | 392.10 | 537.35 | 856.71 | 17.56 | 17.13 |
| hybrid/quiet | 13207 | 114.00 | 330.00 | 454.00 | 858.94 | 19.13 | 12.15 |

## D. Residual corrections on the test split

Both raw residual and deployed Hybrid−Classic are measured; the latter includes clipping and rounding.

| Correction / Classic absolute range | Mean | Std | Median abs | p95 abs | Sign flips % | Exceeds Classic magnitude % |
|---|---:|---:|---:|---:|---:|---:|
| deployed_hybrid_minus_classic/all | -2.49 | 537.75 | 208.00 | 1223.20 | 23.94 | 59.91 |
| deployed_hybrid_minus_classic/0_to_100 | -9.85 | 411.05 | 118.00 | 1154.35 | 35.97 | 78.86 |
| deployed_hybrid_minus_classic/100_to_300 | -22.04 | 529.12 | 212.00 | 1266.40 | 22.12 | 56.84 |
| deployed_hybrid_minus_classic/300_to_800 | 15.16 | 718.40 | 565.00 | 1190.00 | 12.41 | 52.72 |
| deployed_hybrid_minus_classic/800_to_1500 | 48.87 | 524.35 | 370.50 | 675.75 | 3.02 | 3.02 |
| deployed_hybrid_minus_classic/1500_to_inf | 139.97 | 903.18 | 390.00 | 1542.40 | 1.10 | 1.10 |
| raw_residual/all | -2.06 | 544.51 | 208.38 | 1232.99 | 24.02 | 60.22 |
| raw_residual/0_to_100 | -9.78 | 414.38 | 117.61 | 1154.21 | 36.13 | 79.19 |
| raw_residual/100_to_300 | -21.97 | 533.97 | 211.54 | 1284.76 | 22.16 | 56.94 |
| raw_residual/300_to_800 | 16.29 | 729.26 | 565.23 | 1241.44 | 12.41 | 53.36 |
| raw_residual/800_to_1500 | 53.42 | 550.49 | 408.91 | 736.89 | 3.02 | 3.27 |
| raw_residual/1500_to_inf | 120.71 | 866.24 | 323.66 | 1471.20 | 1.10 | 1.10 |

## E. Clipping

| Population | At/beyond ±1500 % |
|---|---:|
| train_labels | 24.696 |
| validation_labels | 24.627 |
| test_labels | 24.567 |
| ml | 5.873 |
| hybrid | 8.321 |
| direct_raw | 5.809 |
| hybrid_raw | 8.253 |

| Raw evaluator / tolerance | New tied pairs % | Affected parents % |
|---|---:|---:|
| direct_raw_tolerance_0 | 1.5679644638920658 | 9.51417004048583 |
| direct_raw_tolerance_5 | 1.5687931977524738 | 9.51417004048583 |
| hybrid_raw_tolerance_0 | 2.685097707722142 | 12.753036437246964 |
| hybrid_raw_tolerance_5 | 2.6763960021878574 | 12.955465587044534 |

A new tie requires raw separation greater than the tolerance and separation after clipping no greater than it. Tolerance 0 is exact, 5 cp is near. Rounding is excluded from this attribution. Boundary labels cannot distinguish naturally exact ±1500 values from censored values, and original unbounded targets cannot be recovered.

## F. Actual depth-3 search evaluations

Uniform reservoir over static evaluation events per search evaluator, including quiescence stand-pat, not terminal mate scores. Repeated positions are retained; more expensive roots contribute more events. Independent fresh TT per root/mode. Root ordering is a seeded random held-out subset. No trusted leaf targets are implied. Incoming -1 denotes root/unknown.

| Search evaluator | Events seen | Sampled | Mean ply | Captures % | Classic median abs | ML median abs | Hybrid median abs |
|---|---:|---:|---:|---:|---:|---:|---:|
| classic | 26563 | 1000 | 5.46 | 54.90 | 272.50 | 193.00 | 254.00 |
| ml | 26341 | 1000 | 5.36 | 56.30 | 265.00 | 192.50 | 265.00 |
| hybrid | 36534 | 1000 | 5.01 | 56.80 | 255.00 | 161.00 | 221.00 |

Full JSON contains all requested thresholds/percentiles, raw/unclipped outputs, leaf score/correction statistics, search summaries, model IDs, dataset hashes, and sample indices. The companion `.samples.jsonl` retains every sampled child and leaf.

## Interpretation and alpha pilots

The frozen neural models fit clipped held-out Stockfish labels better than Classic, while the supplied depth-3 paired matches favor Classic. These are different measurements. Correction magnitudes, local changes and clipping are diagnostic observations, not proof of the cause. Sibling ranking is unavailable without complete trusted child labels.

Existing tournament outcomes are recorded in JSON with their finite-opening bootstrap uncertainty. Global MAE, local stability, and clipping alone do not identify the cause of weaker play. Use the paired alpha commands in `DIAGNOSTICS.md`; do not select a final alpha solely on these 16 openings.
