# External Stockfish calibration

Phase: **final**. Complete: True. Valid: True.
Stockfish UCI_Elo calibrated under this exact **250 ms/move** protocol. This is not a FIDE, Chess.com, Lichess or universal engine rating.

Stockfish: Stockfish 19; supported UCI_Elo [1320, 3190].
Model `v2-residual-3fb0a29e8514af8c`, alpha 0.25. Threads 1; Hash 64 MiB.
Protocol SHA-256: `2aabe0dc1c9c0d18467d1d93bd1e513d16e5b7234bb9f213cdea5ea45bf238a5`.
Opening manifest SHA-256: `58520f80a735353a7366d782b38af9ce246110b1ee4c55a6f422fb400f60490e`.

| SF UCI_Elo | Games | W/D/L | Score | Opening-cluster 95% CI | White score | Black score | Avg plies |
|---:|---:|---|---:|---|---:|---:|---:|
| 1520 | 128 | 78/18/32 | 67.97% | 60.55–75.39% | 71.09% | 64.84% | 99.0 |
| 1620 | 128 | 58/19/51 | 52.73% | 44.91–60.94% | 50.78% | 54.69% | 109.6 |
| 1720 | 128 | 46/24/58 | 45.31% | 37.50–52.73% | 54.69% | 35.94% | 105.8 |
| 1820 | 128 | 34/13/81 | 31.64% | 23.44–40.62% | 32.03% | 31.25% | 104.1 |

Termination counts by opponent level:

- 1520: {'checkmate': 110, 'insufficient_material': 1, 'repetition': 17}
- 1620: {'checkmate': 109, 'repetition': 16, 'max_ply_draw': 1, 'insufficient_material': 2}
- 1720: {'checkmate': 104, 'insufficient_material': 1, 'repetition': 22, 'max_ply_draw': 1}
- 1820: {'repetition': 12, 'checkmate': 115, 'insufficient_material': 1}

Actual move timings (harness response includes IPC; search timing excludes it when reported):

- chessai: `{"moves": 24166, "mean_response_ms": 235.94260531321586, "mean_search_ms": 235.65588944798506, "max_search_ms": 250.2243, "searches_over_budget": 22651}`
- stockfish: `{"moves": 24171, "mean_response_ms": 241.48194116893308, "mean_search_ms": 241.22332547267388, "max_search_ms": 256, "searches_over_budget": 527}`

Calibration: `{"estimate": null, "ci95": null, "method": "linear interpolation of monotone score ladder at 50%", "bootstrap_unit": "opening, both colors, jointly across levels", "bootstrap_iterations": 5000, "bootstrap_identified_fraction": 0.8994, "observed_crossing": 1656.842105263158, "reason": "Insufficient independent clusters or unstable 50% bracket; no reliable calibrated estimate", "phase": "final"}`.

Development/bracketing and smoke results are not final estimates. Bootstrap resamples complete opening pairs jointly across levels. Sparse/extreme results can give degenerate score intervals; uncertainty is conditional on this fixed suite and engine version. A missing or unstable 50% bracket produces no calibrated estimate. Stockfish strength-limited play and timed search can vary even with fixed opening order; the seed does not control Stockfish internal randomness.
