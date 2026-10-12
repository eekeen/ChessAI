# Held-out evaluator validation: heldout-openings-v1

**Status update:** this 32-position suite has now been used for validation and
the candidate is frozen at alpha **0.25**. The original protocol below is retained
as history. Do not tune further on it. Use the [64-position FINAL protocol](FINAL.md)
for final testing. Validation outcomes were not inspected while constructing that set.

The original 16-position `common-openings-v1` suite is **development data**.
It has already informed alpha inspection/tuning. Do not use it again to select
the final alpha. Its moves, ordering, default CLI selection and version are unchanged.

The new, frozen `heldout-openings-v1` contains 32 legal positions after 8–10 plies.
Lines were chosen for opening-family coverage without consulting engine scores,
match results or alpha performance. Coverage includes e4/e5, three Sicilians,
three French structures, Caro-Kann, Scandinavian, Queen's Gambit, Slav/Semi-Slav,
King's/Queen's/Nimzo-Indian, English, Reti, Catalan, Dutch and Benoni.

This is held out from opening-based evaluator development, not a claim that
similar structures or positions never appeared in model training. Common opening
prefixes are shared; the actual starting positions are distinct. Models and
production alpha/default evaluator are unchanged.

## Frozen artifacts and overlap verification

- [Development manifest](suites/common-openings-v1.tsv)
- [Held-out manifest](suites/heldout-openings-v1.tsv)
- Implementation: `src/benchmark/OpeningSuites.cpp`

The TSV header is the suite version; each subsequent row contains name, plies,
normalized four-field FEN and the complete legal UCI move sequence. Held-out
manifest SHA-256 (UTF-8, LF):
`77236baca02e42a32ee53ee3f60e385f3e764a62ed1c54c0114c88f5cbea9a82`.

The C++ test replays every line, checks legality, length, uniqueness and FEN
round-trip, and proves no held-out endpoint matches **any development endpoint
or intermediate position**. Normalization includes placement, side, ordered
castling rights and en-passant; a stronger second check ignores en-passant too.
The CLI test compares names, moves and FENs against the frozen manifests.
Development sequences were additionally checked against the existing historical
`classic_vs_hybrid_depth3_32.json` results.

No match results can rewrite the suite. Do not edit/rebalance it based on results,
discard unfavorable openings, or search additional alpha values on it. Any future
independent suite needs an explicit new version, leaving this one intact.

To inspect without evaluating or playing:

```powershell
./build/Release/ChessAI_tournament.exe --opening-suite heldout --list-openings
```

## Build

```powershell
$cmake = 'C:/Program Files (x86)/Microsoft Visual Studio/2019/Community/Common7/IDE/CommonExtensions/Microsoft/CMake/CMake/bin/cmake.exe'
& $cmake -S . -B build
& $cmake --build build --config Release
```

## Preregistered fixed-depth comparisons (commands only; not run)

Both commands use the same frozen models, 32 positions, shuffled order and seed.
Each position is played twice, with evaluator colors reversed. Every evaluator
plays 32 games as White and 32 as Black. Separate TTs are cleared for every game;
no GUI weakening is used. Alpha cannot affect opening selection/order.

A: Classic versus Hybrid alpha 0.10:

```powershell
./build/Release/ChessAI_tournament.exe --opening-suite heldout --white classic --black hybrid --hybrid-alpha 0.10 --games 64 --depth 3 --seed 12345 --max-plies 300 --output benchmarks/heldout_v1_alpha_010_depth3.json
```

B: Classic versus Hybrid alpha 0.25:

```powershell
./build/Release/ChessAI_tournament.exe --opening-suite heldout --white classic --black hybrid --hybrid-alpha 0.25 --games 64 --depth 3 --seed 12345 --max-plies 300 --output benchmarks/heldout_v1_alpha_025_depth3.json
```

There are no results yet. Neither these matches nor timed follow-ups were run
during implementation. Regression tests validate held-out legality/schedules
without playing held-out games. No 0.50/0.75/1.00 held-out experiment is provided.

## Report interpretation

Console and JSON contain evaluator W/L/D, score %, Elo (Classic minus Hybrid),
95% opening-cluster bootstrap score interval, average total plies, termination
counts, and W/L/D/points/score % split by evaluator color. JSON additionally
contains the Elo interval, all moves, suite version/selection, normalized starting
FEN, settings, model IDs, and game-level results.

Relevant JSON fields:

```text
config.opening_suite = "heldout-openings-v1"
config.opening_suite_selection = "heldout"
summary.evaluators.classic / hybrid
summary.by_evaluator_color.classic.white / black
summary.by_evaluator_color.hybrid.white / black
summary.elo_first_minus_second
summary.uncertainty.score_first_ci95
summary.uncertainty.elo_first_minus_second_ci95
summary.average_plies
summary.termination_counts
```

Elo is estimated only for scores strictly between zero and one. Bootstrap
resamples the 32 opening clusters, keeping each reversed-color pair together.
To read the Hybrid score interval from the Classic interval `[lo, hi]`, use
`[1-hi, 1-lo]`; reverse/negate the Elo bounds. Null Elo endpoints at score 0/1
are unbounded. Intervals describe this finite suite; related opening families
and comparing two candidates limit generalization. A CI overlapping 50% does
not establish equal strength. Keep max-ply draws visible and do not claim
improvement unless the uncertainty supports it.

## Conditional timed follow-up (manual only)

If alpha 0.10 performs competitively in A after examining score, uncertainty,
color split and draw reasons, its corresponding 250 ms/move command is:

```powershell
./build/Release/ChessAI_tournament.exe --opening-suite heldout --white classic --black hybrid --hybrid-alpha 0.10 --games 64 --time-ms 250 --seed 12345 --max-plies 300 --output benchmarks/heldout_v1_alpha_010_250ms.json
```

If alpha 0.25 performs competitively in B, use:

```powershell
./build/Release/ChessAI_tournament.exe --opening-suite heldout --white classic --black hybrid --hybrid-alpha 0.25 --games 64 --time-ms 250 --seed 12345 --max-plies 300 --output benchmarks/heldout_v1_alpha_025_250ms.json
```

These are conditional templates, not recommendations based on unmeasured results.
Nothing triggers them automatically. They test transfer to a time budget on the
same positions, not an independent new opening sample. Do not use this set to
propose/tune new alpha values or change production defaults automatically.
