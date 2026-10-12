# FINAL untouched evaluator test protocol

The candidate is frozen at **Hybrid alpha = 0.25**. Do not tune alpha further.
The 16-position development set informed tuning. The 32-position validation set
(`--opening-suite heldout`) has already compared 0.10 and 0.25. Neither is the
final test set. Their move sequences/manifests remain unchanged.

## Frozen final suite

- CLI selection: `--opening-suite final`
- Version: **final-openings-v1**
- [Manifest](suites/final-openings-v1.tsv): 64 unique legal positions, 10 or 12 plies.
- Source: `src/benchmark/FinalOpenings.cpp`.
- SHA-256 of UTF-8/LF manifest:
  `3f5e12a70b053741d4c8b8664684f384c52d60d79dc7331f0b9c3c2b5a2445c7`.

The lines were authored for opening-family diversity without consulting evaluator
scores or previous match outcomes. They span e4/e5, eight Sicilian lines, French,
Caro-Kann, Scandinavian, Pirc/Modern, Alekhine, Queen's Gambit, Slav/Semi-Slav,
King's/Queen's/Nimzo-Indian, English, Reti, Dutch, Benoni/Benko, Catalan, Budapest
and Gruenfeld structures. Every position is played once per evaluator color.

Legal replay, duplicate and overlap checks passed before freezing the manifest.
No final endpoint matches any of the **215 distinct normalized positions** in
the development/validation lines, including their endpoints and all intermediate
positions. The primary comparison uses four FEN fields: placement, side,
canonical castling rights and en-passant. Clocks are ignored. An additional check
ignores en-passant as well, avoiding differences in EP serialization conventions.

Opening families and early prefixes are necessarily shared; this is an untouched
set of benchmark starting positions, not proof of independence from every model
training position or previously searched node. Final positions were not scored
or searched during construction. No final matches have been run by this task.

**Never modify, filter, rebalance or regenerate this final suite after seeing
results.** Do not select further alpha values from it. Tests enforce its frozen
manifest and the unchanged earlier suites. Any future new test set requires a
separate explicit version; preserve this version and all its outcomes.

## Build

```powershell
$cmake = 'C:/Program Files (x86)/Microsoft Visual Studio/2019/Community/Common7/IDE/CommonExtensions/Microsoft/CMake/CMake/bin/cmake.exe'
& $cmake -S . -B build
& $cmake --build build --config Release
```

## Exactly two final experiments

Commands are provided only; neither is run automatically. Both use alpha 0.25,
128 games, seed **8675309**, the same 64 positions and identical paired-color
order. Each evaluator plays 64 games as White and 64 as Black. Both sides use
the same search implementation/settings, no GUI weakening, and separate TTs
cleared at every game boundary. The 300-ply safety cap includes opening plies.

1. Fixed depth three:

```powershell
./build/Release/ChessAI_tournament.exe --opening-suite final --white classic --black hybrid --hybrid-alpha 0.25 --games 128 --depth 3 --seed 8675309 --max-plies 300 --output benchmarks/final_v1_alpha025_depth3.json
```

2. 250 ms per move:

```powershell
./build/Release/ChessAI_tournament.exe --opening-suite final --white classic --black hybrid --hybrid-alpha 0.25 --games 128 --time-ms 250 --seed 8675309 --max-plies 300 --output benchmarks/final_v1_alpha025_250ms.json
```

Do not run other alpha values or conditionally replace unfavorable positions.
Do not pool the two search regimes as independent opening samples. The two
experiments test the frozen candidate under different search budgets.

## Reports and model identity

No numerical match results are claimed before the commands are run. Both JSON
and console report W/D/L, score %, Elo estimate (Classic minus Hybrid),
opening-cluster bootstrap 95% score CI, evaluator color splits, average plies
and termination counts. JSON additionally includes the Elo CI, per-game moves,
normalized opening FEN, model IDs, suite version and all experiment settings.

Expected frozen model identifiers in this build:

- Classic: `handcrafted-material-pst`
- Hybrid: `v2-residual-3fb0a29e8514af8c`
- Direct model also recorded, though unused in these matches:
  `v2-direct-3b6bb568881c6bd0`

The JSON `models` object identifies the actual compiled models. Verify both
experiments use the same identifiers and alpha; alpha is not encoded in the
model ID. `config.opening_suite` must be `final-openings-v1`.

Report fields:

```text
summary.evaluators.classic / hybrid              # W/L/D, points, score %
summary.elo_first_minus_second                   # Classic minus Hybrid
summary.uncertainty.score_first_ci95              # Classic score fraction
summary.uncertainty.elo_first_minus_second_ci95
summary.by_evaluator_color.classic.white / black # W/L/D, points, score %
summary.by_evaluator_color.hybrid.white / black
summary.average_plies
summary.termination_counts
models
config.opening_suite
config.hybrid_alpha
```

The bootstrap resamples 64 opening clusters, retaining reversed-color games
together (10,000 replicates by default). Related opening families still limit
generalization. Elo is `400 * log10(score / (1-score))` only for scores strictly
between 0 and 1; null interval endpoints at score 0/1 are unbounded. To view the
Hybrid interval, reverse/complement Classic score bounds and reverse/negate Elo
bounds. A CI overlapping equality does not prove equal strength. Keep max-ply
draws separate from chess-rule draws, and do not claim improvement unless the
measurements and uncertainty support it.

## Verification without consuming the final test set

```powershell
./build/Release/opening_suite_tests.exe
python tests/test_opening_manifests.py
```

These replay legal opening moves and validate normalized FENs, frozen hashes,
suite versions and schedules only. They perform no search/evaluation or matches.
The C++ test is registered as `opening_suites` in CTest. Existing production
defaults, ML weights/training and earlier tournament functionality are unchanged.
