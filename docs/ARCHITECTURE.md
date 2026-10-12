# Architecture

ChessAI separates board rules, search, evaluation, game state and presentation. The C++17 `ChessCore` library is shared by the desktop engine and native benchmark programs.

| Module | Responsibility |
|---|---|
| `src/chess/` | Board representation, FEN, moves, legal move generation and special moves |
| `src/engine/Search.cpp` | Iterative deepening, alpha-beta, quiescence, ordering and time limits |
| `src/engine/TranspositionTable.*`, `Zobrist.*` | Position keys, cached bounds and moves |
| `src/engine/Evaluation.*` | Classic material and piece-square evaluation |
| `src/engine/PositionEvaluator.*` | Evaluator selection, residual blend, clipping and rounding |
| `src/engine/MLEvaluationV2.*`, `V2Kernels*` | Feature extraction and native neural inference |
| `src/engine/generated/` | Production model weights |
| `src/game/` | Game controller, move history, game results and GUI difficulty behavior |
| `src/main.cpp` | Line-oriented desktop engine protocol |
| `src/gui/` | Tkinter presentation and engine subprocess client |
| `src/benchmark/` | Headless tournaments, performance, profiling and external calibration adapter |

A GUI action reaches the game controller through the engine subprocess protocol. Search generates legal successors, uses transposition bounds and evaluates leaves. Classic and the residual network contribute to the selected Hybrid evaluator; the completed search returns a move to the controller and GUI. Game rules and history also determine game termination. Search uses mate-distance scores separately from bounded static neural scores.

Production Hybrid uses alpha 0.25 and residual model `v2-residual-3fb0a29e8514af8c`. The MSVC x64 AVX2 translation unit is isolated from portable code. Runtime CPU and OS state checks gate execution; the reference implementation remains available. Sparse active feature indices preserve accumulation order; the tail vectorizes independent neurons without changing final output accumulation order.

The GUI difficulty profiles are gameplay conveniences. Its responsive board orientation is independent of the player's side; side, difficulty and evaluator controls configure the next New Game. Static evaluation is read through the existing protocol, while the last engine response supplies depth and search details. The GUI does not implement chess legality or search. Tournament and calibration entry points use native search directly without GUI weakening. The desktop protocol and calibration adapter are application-specific protocols, not general UCI engines. The external Python harness speaks UCI to Stockfish and independently referees games.

`ChessCoreDiagnostics` is separately instrumented. The optional `CHESSAI_BUILD_PROFILER` target measures static evaluator stages without instrumenting normal production search. The release presentation update changes none of these modules.
