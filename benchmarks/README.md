# Headless evaluator tournament

The candidate is now frozen at alpha **0.25**. See the
[FINAL test protocol](FINAL.md) for `--opening-suite final`, the immutable
64-position suite, and exactly two final experiments. Earlier development and
validation commands below are historical; do not use them for further alpha tuning.

`--opening-suite development` (default) retains the original 16 positions.
`--opening-suite heldout` selects the frozen 32-position validation suite.
See [held-out validation](HELDOUT.md) for overlap tests, reporting, and the two
preregistered 64-game alpha comparisons. The development set must no longer be
used to select the final alpha.

For frozen-model analysis and `--hybrid-alpha` pilot commands, see
[the diagnostics guide](DIAGNOSTICS.md) and [measured report](diagnostic_report.md).

`ChessAI_tournament` compares Classic, V2 Direct (`ml`), and V2 Residual Hybrid
using the exact existing C++ `Search` and `Game` implementations. It never calls
`GameController`, its difficulty/blunder profiles, or its opening-book selector.
No Python or GUI is required to run a match. The Python smoke test is optional.

## Build and run (PowerShell, repository root)

The V2 headers currently present in `src/engine/generated` are compiled into the
executable. Training is not part of the tournament. Missing V2 weights cause an
explicit error; there is no silent substitution of the V1 model or weighted hybrid.

```powershell
$env:Path = 'C:\Program Files (x86)\Microsoft Visual Studio\2019\Community\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin;' + $env:Path
cmake -S . -B build
cmake --build build --config Release --clean-first
```

Primary experiment (200 games, 250 milliseconds per searched move):

```powershell
.\build\Release\ChessAI_tournament.exe --white classic --black hybrid --games 200 --time-ms 250 --seed 42 --max-plies 300 --output benchmarks/classic_vs_hybrid.json
```

The names after `--white` and `--black` describe **game 1**. Game 2 reverses those
assignments with exactly the same forced opening. Every following pair repeats
that pattern. All games use the same time budget (including the slower ML code).
At the full length cap, the default experiment can take roughly four hours;
actual duration depends on game lengths and search timing overhead.

Other comparisons and fixed-depth alternative:

```powershell
.\build\Release\ChessAI_tournament.exe --white classic --black ml --games 200 --time-ms 250 --seed 42 --output benchmarks/classic_vs_ml.json
.\build\Release\ChessAI_tournament.exe --white ml --black hybrid --games 200 --time-ms 250 --seed 42 --output benchmarks/ml_vs_hybrid.json
.\build\Release\ChessAI_tournament.exe --white classic --black hybrid --games 200 --depth 3 --seed 42 --output benchmarks/classic_vs_hybrid_depth3.json
```

`--depth` replaces the timed budget; supplying both `--depth` and `--time-ms` is
an error. Fixed depth equalizes search depth, not wall time or nodes. The default
timed mode uses the existing iterative deepening with maximum search depth 64.
Separate evaluator-specific transposition tables are cleared before **every game**;
neither engine gets entries from the other evaluator or the previous game.

Additional options: `--bootstrap-samples 10000`, `--overwrite`, `--help`.
`--games` must be even and at least two. `--max-plies` includes forced opening
plies and must be at least ten. Existing output files are preserved unless
`--overwrite` is supplied. JSON snapshots are atomically replaced after each
completed pair. Interruption leaves the last complete pair's snapshot; the
current unfinished pair is not included and there is no automatic resume.

## Opening diversity and adjudication

The versioned 16-opening suite contains Italian/e4-e5, Ruy Lopez, Scotch, Petrov,
Sicilian, French, Caro-Kann, Queen's Gambit, Slav, King's Indian, English, Reti,
Nimzo-Indian, Queen's Indian, Scandinavian, and Pirc. Each legal UCI sequence
contains 6–8 plies. The runner validates every opening before play starts and
applies it through `Game::tryMove`, preserving repetition history and move clocks.

Seeded Fisher–Yates shuffles choose the opening order, visiting the full suite
before reshuffling. Both colors are always played for each selected opening.
The seed deterministically controls openings; fixed-depth search is reproducible
within a build. Timed games can vary with scheduling/CPU load even with the same
seed. Run strength benchmarks without other heavy workloads.

Natural terminations come from `Game::getGameState`: checkmate, stalemate,
threefold repetition, fifty-move rule, or insufficient material. This preserves
the engine's automatic draw handling. A still-ongoing game at the length limit
is separately labeled `max_ply_draw`; real terminal conditions take precedence
even on the final allowed ply. Illegal search moves abort as errors, not draws
or forfeits. There is no score-based resignation or evaluation adjudication.

## Report and uncertainty

Every record contains game number, pair, evaluator colors, opening name/index,
forced opening moves, result, termination, total/searched plies, elapsed search
play time, nodes, and the full UCI move list including the opening. The JSON also
records configuration, model identifiers and whether all requested games finished.

Summary includes color wins, draws, each evaluator's wins/losses/draws/points and
score percentage, mean total plies, and counts for all six termination reasons.
A win is 1 point, a draw 0.5, a loss 0. Elo difference is
`400 * log10(score / (1-score))`, for the first evaluator minus the second.
It is `null` when the first evaluator's score is exactly 0 or 1.

The 95% percentile bootstrap resamples **opening clusters**, retaining both colors
and all repeats of the same opening together. This avoids treating deterministic
repeated games as independent evidence. At most 16 opening clusters are available
in this suite even when 200 games are played. Score limits are fractions in [0,1];
Elo limits apply the same monotonic formula. Score limits are null with fewer
than two openings. An Elo endpoint is null/unbounded if its score endpoint is 0/1.

Intervals are conditional on this small predefined suite. All-identical cluster
outcomes can produce a degenerate bootstrap interval that understates uncertainty.
The tool does **not** automatically claim statistical significance. Inspect sample
diversity, interval width, and the number of max-ply draws before interpreting a
score. An interval spanning 50% cannot support a superiority claim. Expand the
opening suite and repeat measurements before making a broad strength claim.

## Tests and short example

```powershell
Push-Location build
ctest -C Release --output-on-failure
Pop-Location
python tests/tournament_smoke.py --engine build/Release/ChessAI_tournament.exe
.\build\Release\ChessAI_tournament.exe --white classic --black hybrid --games 4 --depth 1 --max-plies 10 --seed 42 --output benchmarks/smoke_results.json
```

The smoke match deliberately reaches the safety cap. Its draws are software
validation, **not** evidence of equal playing strength. An abbreviated record is:

```json
{
  "number": 1,
  "pair": 1,
  "white": "classic",
  "black": "hybrid",
  "result": "1/2-1/2",
  "termination": "max_ply_draw",
  "plies": 10
}
```

Actual records also contain all opening and move fields described above. Unit
tests cover color alternation, per-side evaluator selection, legal opening replay,
seed reproducibility, W/D/L accounting, score and Elo calculation, bootstrap
reproducibility, and repeated-opening clustering. CLI tests cover all three
pairings, fixed-depth move reproducibility, timed search, invalid arguments and
JSON consistency. Existing perft and evaluator tests run alongside them.
