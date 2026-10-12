# External playing-strength calibration

This measures **Stockfish-calibrated playing strength under this test protocol**.
It is not a FIDE, Chess.com, Lichess or universal engine rating. No model training,
alpha tuning, search changes or internal strength-suite edits are part of this framework.

ChessAI uses the actual production `ChessCore` via `ChessAI_calibration.exe`:
Hybrid V2 residual, alpha **0.25**, model `v2-residual-3fb0a29e8514af8c`.
The executable is a small private line-protocol adapter, **not a UCI implementation**.
It calls `Search::findBestMoveTimed(board, milliseconds, 64)` directly. There is no
GUI controller, difficulty profile, random weakening or book. Only this adapter
and the build target were added; production evaluation/search sources are unchanged.

## Build and dependencies

Run from the repository root (PowerShell):

```powershell
python -m venv .venv-elo --system-site-packages
.\.venv-elo\Scripts\python.exe -m pip install -r benchmarks/elo/requirements.txt
& 'C:/Program Files (x86)/Microsoft Visual Studio/2019/Community/Common7/IDE/CommonExtensions/Microsoft/CMake/CMake/bin/cmake.exe' --build build --config Release --target ChessAI_calibration
.\.venv-elo\Scripts\python.exe tests/calibration_tests.py
```

For a fresh build, first configure with `cmake -S . -B build -A x64`.
The separate pinned `chess==1.11.2` dependency provides independent legal-move and
game-rule validation. ML dependencies and training are untouched.

## Stockfish discovery and tiny smoke

Supply your installed executable or set `STOCKFISH`. The program otherwise checks
PATH. Missing executables/options fail clearly; it never downloads a binary itself
or substitutes a guessed Elo range.

```powershell
$env:STOCKFISH = 'C:\path\to\stockfish.exe'
.\.venv-elo\Scripts\python.exe benchmarks/elo/calibrate.py detect --stockfish "$env:STOCKFISH" --output benchmarks/elo/stockfish_detection.json
.\.venv-elo\Scripts\python.exe benchmarks/elo/calibrate.py smoke --stockfish "$env:STOCKFISH" --time-ms 250 --max-plies 300 --seed 20260926 --protocol benchmarks/elo/smoke_protocol.json --output benchmarks/elo/smoke_results.json
```

Smoke uses one opening twice, reversed colors, against the advertised minimum
`UCI_Elo` unless `--elos` supplies one supported value. It provides no calibrated
estimate or misleading one-cluster confidence interval. A shorter explicit
`--max-plies` is available for safety-capped smoke tests; caps are reported as draws.

UCI startup sends `uci`, parses all advertised options, waits for `uciok`, sets
options and waits for `readyok`. Required options: `UCI_LimitStrength` (check),
`UCI_Elo` (spin with runtime min/max), `Threads` and `Hash`. Used settings:

| Option | Setting |
|---|---|
| UCI_LimitStrength | true |
| UCI_Elo | Current frozen opponent level, checked against advertised bounds |
| Threads | 1 |
| Hash | 64 MiB by default; `--hash-mb` can change it before freeze |
| Skill Level, if offered | Advertised maximum; UCI_Elo limiting takes precedence |
| Ponder / UCI_Chess960 | false, if offered |
| MultiPV | 1, if offered |
| Move Overhead / nodestime | 0, if offered |
| SyzygyPath | Empty, if offered; no external tablebases |
| Clear Hash | Issued before each game if offered, in addition to `ucinewgame` |

All supported option declarations, applied options, ID/version and executable
SHA-256 are recorded. Each game also records its applied Elo/options.
Stockfish options and ranges are version-dependent; the harness does not use the
example numbers in documentation. See the official
[UCI protocol and options](https://official-stockfish.github.io/docs/stockfish-wiki/UCI-Protocol-and-Stockfish-Commands.html).

## Frozen external openings

`openings-v1.tsv`: **64 positions, 32 named opening families, 10–12 plies**.
Authored common opening lines, validated without evaluating positions or inspecting
match outcomes. There are no duplicate normalized FENs (first four fields, legal
en-passant normalization), and no endpoint overlap with the internal development,
validation or final manifests. Both engines receive the same forced move history.

SHA-256:
`58520f80a735353a7366d782b38af9ce246110b1ee4c55a6f422fb400f60490e`

`openings-v1.freeze.json` records the immutable manifest version/hash. Loader and
tests verify it; the test pins the digest independently. The authored construction
script refuses to overwrite a frozen suite. Never regenerate v1 based on results.
These are curated openings, not a random sample of all possible chess positions.

## Phase A: development/bracketing only

After reviewing the framework and real smoke match:

```powershell
.\.venv-elo\Scripts\python.exe benchmarks/elo/calibrate.py development --stockfish "$env:STOCKFISH" --subset 8 --elo-step 200 --time-ms 250 --hash-mb 64 --max-plies 300 --seed 20260926 --bootstrap 5000 --protocol benchmarks/elo/development_protocol.json --output benchmarks/elo/development_results.json
```

This uses the same fixed eight-opening subset at each automatically generated level:
advertised minimum, increments of 200, and advertised maximum (included even when
the last gap is shorter). There are **16 paired-color games per level**. Opening
ordering is SHA-256/seed based and level order rotates between openings. These
results locate a bracket only; do not use them to tune ChessAI.

Runtime depends on the binary's supported range and actual game lengths. Let
`L = ceil((max_elo - min_elo)/200) + 1`. At 120 searched plies/game, the requested
budgets total about **8 × L minutes**, plus startup/adjudication overhead. Near the
300-ply cap, allow roughly **19.3 × L minutes**, plus overhead and timer overruns.
For example, 10 levels would mean 160 games and approximately 80 minutes at the
120-searched-ply assumption. This is an estimate, not measured Stockfish runtime.

## Freeze final strengths before playing them

After reviewing development results, this selects up to four already tested points
nearest the unique monotone 50% crossing. It fails if the ladder does not identify
a bracket. You may explicitly supply several supported `--elos` values instead,
but choose them from the development phase before any final games.

```powershell
.\.venv-elo\Scripts\python.exe benchmarks/elo/calibrate.py freeze --stockfish "$env:STOCKFISH" --development benchmarks/elo/development_results.json --time-ms 250 --hash-mb 64 --max-plies 300 --seed 20260926 --protocol benchmarks/elo/calibration_protocol.json
```

**This command writes a protocol and runs no games.** It freezes engine binary
hashes, model/alpha, the manifest and every opening, strength points, exact game
order/colors, time control, threads/hash, adjudication, bootstrap settings and
the harness implementation/Python environment. The file has both a content digest
and a separate file seal; existing protocols cannot be overwritten through the CLI.

Only after human review, copy the printed protocol content digest into:

```powershell
.\.venv-elo\Scripts\python.exe benchmarks/elo/calibrate.py final --stockfish "$env:STOCKFISH" --protocol benchmarks/elo/calibration_protocol.json --protocol-sha256 '<reviewed content digest>' --output benchmarks/elo/final_results.json
```

Final game settings come exclusively from that protocol. Supply the same
`--hash-mb` when a non-default Stockfish hash was frozen. Every selected level gets
all 64 openings with reversed colors: **128 games/level**. No final run, strength
selection or coarse ladder is automatically launched by setup, tests or smoke.
No real final protocol is supplied in advance of actual bracketing results.

Do not modify engines or harness after final freeze. A bug that affects games
invalidates the **whole affected run**. Record the bug, retain the invalid report,
create a new protocol/version and rerun the entire affected experiment only after
review. There is no selective replay/resume facility.

## Game rules, clocks and failures

The Python referee keeps the entire legal history, including forced openings.
Stockfish receives `position startpos moves ...` and `go movetime 250`; ChessAI
receives the same current FEN and calls production timed search with 250 ms.
Stockfish sees repetition history; ChessAI retains its existing Board-based search
interface. This does not add repetition awareness to ChessAI's search.

Both sides clear TT between games and keep it between moves. ChessAI retains its
production 262,144-entry/8 MiB TT; Stockfish uses the documented fixed 64 MiB default.
This memory asymmetry is part of the protocol, not an equal-hash comparison.
Both use one search thread; pondering and evaluation-based adjudication are disabled.

Mate/stalemate take precedence. Draws occur on the actual third repetition,
100 halfmoves without a pawn move/capture, or python-chess insufficient material.
The referee automatically exercises claims once reached; it does not claim an
anticipated future repetition/fifty-move draw. Maximum plies include the opening.
Illegal moves, engine crashes, protocol errors or response timeouts are recorded as
forfeits **and invalidate/stop the whole run**, withholding any calibration estimate.
Ctrl+C produces an explicitly incomplete/invalid report, not a resumable selection.

The intended budget is identical, but exact wall times depend on engine stop checks.
The default **2,000 ms response grace** is an IPC/hang guard, not extra search time:
each engine still receives 250 ms. JSON records internal search time when available,
response time, requested time and overruns for each move. ChessAI's search timer
excludes FEN parsing, legal validation and pipe transport. Stockfish's internal
time comes from its last UCI info line; response time is always measured externally.

## Reporting and uncertainty

JSON contains every opening, move, color, result, termination, ply count, elapsed
timing, engine/options/hashes, CPU/platform and frozen protocol. Atomic checkpoints
remain marked incomplete until the entire plan succeeds; output paths cannot be
reused. Markdown gives W/D/L, score, color split, length, terminations and timing.

Score uncertainty resamples **opening clusters**, keeping both colors together.
For the cross-level estimate, the same sampled opening IDs are used at every level.
The method interpolates a monotone score ladder around 50%; it refuses extrapolation,
non-monotone/noisy ladders and ambiguous plateaus. Failed/unbracketed bootstrap
replicates are treated conservatively at interval tails; no finite estimate is
published unless a finite 95% interval is identified. A single opening gets no CI.

Limitations: small development subsets are noisy; all-win/all-loss bootstrap score
intervals can be degenerate; the manifest is curated; Stockfish limiting includes
internal randomness not controlled by the opening seed; timed search depends on
hardware/load; and Stockfish's UCI_Elo scale was calibrated under a different time
control. Do not map the result to human/site ratings. The full suite includes the
development subset by design; ChessAI itself must remain frozen throughout.

## Tests and current validation artifacts

```powershell
.\.venv-elo\Scripts\python.exe tests/calibration_tests.py
```

Tests use an explicitly fake UCI engine and the real native adapter: handshake,
option/range parsing, legal exchange/side handling, castling, en passant, promotion,
mate, stalemate, insufficient material, repetition, fifty-move rule, scheduling,
crash/timeout/illegal-move invalidation, accounting, opening-cluster bootstrap,
protocol seals/environment/binary binding and native legality on all 64 openings.

`fixture_smoke_results.json/.md` is labelled **FAKE UCI opponent**, not a Stockfish
strength result. It exists solely to inspect move exchange when an installed
Stockfish executable is unavailable. `fixture_smoke_protocol.json` cannot be used
as a final or development protocol. `validation_status.json` records the local
validation/detection status. Existing internal suites and results remain untouched.

Independent rules implementation: [python-chess documentation](https://python-chess.readthedocs.io/en/latest/).
