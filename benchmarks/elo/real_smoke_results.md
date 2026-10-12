# External Stockfish calibration

Phase: **smoke**. Complete: True. Valid: True.
Stockfish UCI_Elo calibrated under this exact **250 ms/move** protocol. This is not a FIDE, Chess.com, Lichess or universal engine rating.

Stockfish: Stockfish 19; supported UCI_Elo [1320, 3190].
Model `v2-residual-3fb0a29e8514af8c`, alpha 0.25. Threads 1; Hash 64 MiB.
Protocol SHA-256: `b5f602231429e06b84948839dea795c125def1fa947063ec1a7107e286b44906`.
Opening manifest SHA-256: `58520f80a735353a7366d782b38af9ce246110b1ee4c55a6f422fb400f60490e`.

| SF UCI_Elo | Games | W/D/L | Score | Opening-cluster 95% CI | White score | Black score | Avg plies |
|---:|---:|---|---:|---|---:|---:|---:|
| 1320 | 2 | 1/0/1 | 50.00% | n/a | 100.00% | 0.00% | 100.0 |

Termination counts by opponent level:

- 1320: {'checkmate': 2}

Actual move timings (harness response includes IPC; search timing excludes it when reported):

- chessai: `{"moves": 90, "mean_response_ms": 241.4999999985513, "mean_search_ms": 241.09965666666676, "max_search_ms": 250.1078, "searches_over_budget": 86}`
- stockfish: `{"moves": 90, "mean_response_ms": 244.96666666689433, "mean_search_ms": 244.7, "max_search_ms": 251, "searches_over_budget": 5}`

Calibration: `{"estimate": null, "ci95": null, "reason": "Fewer than two independent opening clusters; no uncertainty estimate", "phase": "smoke"}`.

Development/bracketing and smoke results are not final estimates. Bootstrap resamples complete opening pairs jointly across levels. Sparse/extreme results can give degenerate score intervals; uncertainty is conditional on this fixed suite and engine version. A missing or unstable 50% bracket produces no calibrated estimate. Stockfish strength-limited play and timed search can vary even with fixed opening order; the seed does not control Stockfish internal randomness.
