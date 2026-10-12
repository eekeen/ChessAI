# External Stockfish calibration

Phase: **development**. Complete: True. Valid: True.
Stockfish UCI_Elo calibrated under this exact **250 ms/move** protocol. This is not a FIDE, Chess.com, Lichess or universal engine rating.

Stockfish: Stockfish 19; supported UCI_Elo [1320, 3190].
Model `v2-residual-3fb0a29e8514af8c`, alpha 0.25. Threads 1; Hash 64 MiB.
Protocol SHA-256: `3588cad462dfc769ef9b5a323f820a9ff00c8c5fdb8b0dc5e748b3f62956767c`.
Opening manifest SHA-256: `58520f80a735353a7366d782b38af9ce246110b1ee4c55a6f422fb400f60490e`.

| SF UCI_Elo | Games | W/D/L | Score | Opening-cluster 95% CI | White score | Black score | Avg plies |
|---:|---:|---|---:|---|---:|---:|---:|
| 1320 | 16 | 15/1/0 | 96.88% | 90.62–100.00% | 93.75% | 100.00% | 73.8 |
| 1520 | 16 | 11/3/2 | 78.12% | 59.38–93.75% | 87.50% | 68.75% | 103.2 |
| 1720 | 16 | 7/1/8 | 46.88% | 25.00–68.75% | 43.75% | 50.00% | 115.9 |
| 1920 | 16 | 5/2/9 | 37.50% | 12.50–62.50% | 18.75% | 56.25% | 94.9 |
| 2120 | 16 | 3/2/11 | 25.00% | 6.25–43.75% | 43.75% | 6.25% | 106.9 |
| 2320 | 16 | 1/1/14 | 9.38% | 0.00–28.12% | 12.50% | 6.25% | 117.8 |
| 2520 | 16 | 0/3/13 | 9.38% | 3.12–18.75% | 12.50% | 6.25% | 115.8 |
| 2720 | 16 | 0/0/16 | 0.00% | 0.00–0.00% | 0.00% | 0.00% | 117.4 |
| 2920 | 16 | 0/0/16 | 0.00% | 0.00–0.00% | 0.00% | 0.00% | 118.2 |
| 3120 | 16 | 0/0/16 | 0.00% | 0.00–0.00% | 0.00% | 0.00% | 74.2 |
| 3190 | 16 | 0/0/16 | 0.00% | 0.00–0.00% | 0.00% | 0.00% | 75.6 |

Termination counts by opponent level:

- 1320: {'checkmate': 15, 'repetition': 1}
- 1520: {'checkmate': 13, 'repetition': 3}
- 1720: {'checkmate': 15, 'repetition': 1}
- 1920: {'checkmate': 14, 'repetition': 1, 'insufficient_material': 1}
- 2120: {'checkmate': 14, 'repetition': 2}
- 2320: {'checkmate': 15, 'repetition': 1}
- 2520: {'repetition': 3, 'checkmate': 13}
- 2720: {'checkmate': 16}
- 2920: {'checkmate': 16}
- 3120: {'checkmate': 16}
- 3190: {'checkmate': 16}

Actual move timings (harness response includes IPC; search timing excludes it when reported):

- chessai: `{"moves": 7989, "mean_response_ms": 230.1448241331076, "mean_search_ms": 229.83053473526112, "max_search_ms": 252.3801, "searches_over_budget": 7292}`
- stockfish: `{"moves": 8030, "mean_response_ms": 239.56475716062786, "mean_search_ms": 239.2890410958904, "max_search_ms": 252, "searches_over_budget": 419}`

Calibration: `{"estimate": null, "ci95": null, "method": "linear interpolation of monotone score ladder at 50%", "bootstrap_unit": "opening, both colors, jointly across levels", "bootstrap_iterations": 5000, "bootstrap_identified_fraction": 0.2824, "observed_crossing": 1700.0, "reason": "Insufficient independent clusters or unstable 50% bracket; no reliable calibrated estimate", "phase": "development"}`.

Development/bracketing and smoke results are not final estimates. Bootstrap resamples complete opening pairs jointly across levels. Sparse/extreme results can give degenerate score intervals; uncertainty is conditional on this fixed suite and engine version. A missing or unstable 50% bracket produces no calibrated estimate. Stockfish strength-limited play and timed search can vary even with fixed opening order; the seed does not control Stockfish internal randomness.
