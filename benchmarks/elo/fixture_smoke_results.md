# External Stockfish calibration

**FAKE UCI OPPONENT — integration test only. No external playing strength was measured.**

Phase: **test_fixture**. Complete: True. Valid: True.
Stockfish UCI_Elo calibrated under this exact **5 ms/move** protocol. This is not a FIDE, Chess.com, Lichess or universal engine rating.

Stockfish: Stockfish FAKE TEST FIXTURE; supported UCI_Elo [1200, 2600].
Model `v2-residual-3fb0a29e8514af8c`, alpha 0.25. Threads 1; Hash 64 MiB.
Protocol SHA-256: `dd2c9b9edd5b3a67789d4d5634de929b70ea7e4f8c5eb8deebf0f6a54ab04d66`.
Opening manifest SHA-256: `58520f80a735353a7366d782b38af9ce246110b1ee4c55a6f422fb400f60490e`.

| SF UCI_Elo | Games | W/D/L | Score | Opening-cluster 95% CI | White score | Black score | Avg plies |
|---:|---:|---|---:|---|---:|---:|---:|
| 1200 | 2 | 0/2/0 | 50.00% | n/a | 50.00% | 50.00% | 14.0 |

Termination counts by opponent level:

- 1200: {'max_ply_draw': 2}

Actual move timings (harness response includes IPC; search timing excludes it when reported):

- chessai: `{"moves": 4, "mean_response_ms": 3.9999999571591616, "mean_search_ms": 5.0177, "max_search_ms": 5.0288, "searches_over_budget": 4}`
- stockfish: `{"moves": 4, "mean_response_ms": 0.0, "mean_search_ms": 1.0, "max_search_ms": 1, "searches_over_budget": 0}`

Calibration: `{"estimate": null, "ci95": null, "reason": "Fewer than two independent opening clusters; no uncertainty estimate", "phase": "test_fixture"}`.

Development/bracketing and smoke results are not final estimates. Bootstrap resamples complete opening pairs jointly across levels. Sparse/extreme results can give degenerate score intervals; uncertainty is conditional on this fixed suite and engine version. A missing or unstable 50% bracket produces no calibrated estimate. Stockfish strength-limited play and timed search can vary even with fixed opening order; the seed does not control Stockfish internal randomness.
