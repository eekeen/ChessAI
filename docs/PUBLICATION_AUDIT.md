# Final pre-ship audit — 2026-10-12

**SHIP READY:** the project source is MIT licensed and all twelve pieces now use
verified public-domain Livius artwork. GUI/promotion checks and the publication
audit passed. Engine and frozen evidence remain unchanged.
Git was not initialized; no commit, tag, push or strength recalibration was performed.

This audit supersedes the earlier publication summary. `RELEASE_AUDIT.md` and
`RELEASE_CHECK.md` retain explicitly labelled historical release measurements.
The new checks below use regression/synthetic positions, not frozen strength suites.

## A. Files changed

- Add `LICENSE`: MIT, copyright 2026 ChessAI contributors, as selected by the owner.
- Replace all twelve `src/gui/assets/pieces/{w,b}{K,Q,R,B,N,P}.png` files with
  transparent 256 × 256 rasterizations of the public-domain Livius set.
- Add `src/gui/assets/pieces/livius/`: twelve original SVGs, exact upstream
  dedication/README and revision/hash provenance. No SVG geometry/colors changed.
- `src/gui/gui.py`: asset loading only; remove the old unverified download
  fallback and report missing bundled assets through the existing error handler.
  Every other GUI function/class and all gameplay functions are structurally unchanged.
- `THIRD_PARTY_NOTICES.md`: exact source/revision/dedication, author credit,
  conversion details and separation of project MIT and third-party terms.
- `README.md`, `docs/images/README.md`, `docs/RELEASE_AUDIT.md`: resolved licensing
  status; `docs/PUBLICATION_AUDIT.md`: this rerun audit.
- Recapture both real GUI screenshots with the replacement artwork.

No engine, search, ML, time management, gameplay logic, frozen benchmark or
calibration file was modified. No Git operations were performed.

## B. Files deleted and duplicate/dead-file decisions

No files were deleted in this pass. During the preceding cleanup, automatic
approval review rejected the deletion command
for `build/publication-audit/`, root `Testing/`, `README.txt` and the empty unused
`ml/generate_dataset.py`, without a more detailed reason. All four destinations
are excluded from publication. Their retention is not a publication blocker.
The current audit's own evidence under `build/pre-ship-audit/` is also ignored.

There are no identical nonempty publication candidates. Empty `.gitkeep` files
are intentional. Empty `src/engine/Engine.cpp` remains a CMake source;
`Engine.h` remains an existing engine placeholder. Removing engine source is
outside this cleanup's scope. The empty unused ML placeholder has no imports,
CMake references or documented command and is excluded. V1 research scripts,
recorded experiments and old profiler measurements remain useful historical
reproducibility evidence; age alone is not a deletion reason. No frozen evidence
was removed. All twelve piece PNGs are used; three WAVs match code generation.

## C. Complete tree classification and root decisions

The rerun inventory snapshot contains **4,247 files**, with categories:

| Category | Files | Decision |
|---|---:|---|
| A — MUST SHIP | 82 | Build/runtime source, deployed weights, schemas, regressions and licensed assets |
| B — SHOULD SHIP | 155 | Documentation, screenshots, artwork provenance and research evidence |
| C — SHOULD BE IGNORED | 3979 | Generated builds, caches, local dependencies, raw data and checkpoints |
| D — SHOULD BE REMOVED | 29 | Disposable scratch/empty placeholders; all excluded despite local retention |
| E — NEEDS MANUAL REVIEW | 0 | No unresolved manual-review blockers |

The recursive per-file classification, exact first-add manifest, exclusion
manifest and scan line catalogue are local audit evidence, not public deliverables.
They reside in ignored `build/pre-ship-audit/` as `tree-classification.csv`,
`candidate-files.txt`, `ignored-files.txt`, `privacy-pattern-matches.csv` and
`debug-matches.csv`. Every existing regular file was inventoried, including
virtual environment/vendor files, build directories and the new audit's output.

The intended public root is `.gitignore`, `CMakeLists.txt`, `README.md`, `VERSION`,
`run_chessai.bat`, `LICENSE`, `THIRD_PARTY_NOTICES.md`, and `src/`, `ml/`, `benchmarks/`,
`tests/`, `docs/`. `LICENSE` is now present under the owner-selected MIT terms.
Locally retained extra root directories are `build/`, seven `build-*` directories,
`.venv-elo/`, `stockfish/`, `Testing/`: compilation/validation/profiling tools,
installed test dependencies and external opponent tools, all ignored. Empty
`README.txt` is ignored. No local IDE configuration is needed to build or run.

Ignore rules exclude CMake/compiler/CTest/IDE products, Python bytecode/caches,
virtual environments, downloaded Stockfish, NPZ/raw datasets, unnecessary PyTorch
checkpoints, profiler scratch, logs, temporary files, environment files, OS metadata
and editor swaps. Explicit exceptions retain dataset metadata, metrics, histories,
production headers and feature schema. No Git initialization was used to test
inclusion; filesystem matching evaluates parent exclusions and ordered exceptions.

## D. Every large file

Thresholds use decimal bytes: >1,000,000, >10,000,000 and >50,000,000.
There are **53 / 5 / 2** files above those thresholds.
Only five should ship: the two required weight headers and three preserved
benchmark evidence files. No public candidate exceeds 20 MiB. Raw training data,
Stockfish, conversion-tool binaries and all build/checkpoint outputs are ignored.
The existing oversized files are excluded. GitHub's 50 MiB warning and 100 MiB
ordinary-Git limit are documented in its
[file-size guidance](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github).

| Path | Bytes | MiB | Ship? | Purpose |
|---|---:|---:|---|---|
| `benchmarks/diagnostic_report.samples.jsonl` | 4,867,387 | 4.642 | Yes | Preserved benchmark evidence |
| `benchmarks/elo/development_results.json` | 5,978,129 | 5.701 | Yes | Preserved benchmark evidence |
| `benchmarks/elo/final_results.json` | 17,999,457 | 17.166 | Yes | Preserved benchmark evidence |
| `build/asset-tools/resvg_py/resvg_py.pyd` | 2,708,992 | 2.583 | No | Ignored audit output/conversion dependency |
| `build/ChessAI.dir/Debug/GameController.obj` | 1,110,241 | 1.059 | No | Ignored generated build/profiler output |
| `build/Debug/ChessAI.ilk` | 2,232,352 | 2.129 | No | Ignored generated build/profiler output |
| `build/Debug/ChessAI.pdb` | 3,567,616 | 3.402 | No | Ignored generated build/profiler output |
| `build/pre-ship-audit/debug-matches.csv` | 2,099,354 | 2.002 | No | Ignored audit output/conversion dependency |
| `build/pre-ship-audit/privacy-pattern-matches.csv` | 1,818,112 | 1.734 | No | Ignored audit output/conversion dependency |
| `build/Release/ChessAI_tournament.exe` | 1,096,704 | 1.046 | No | Ignored generated build/profiler output |
| `build/Release/ChessCore.lib` | 1,869,612 | 1.783 | No | Ignored generated build/profiler output |
| `build/Release/ChessCoreDiagnostics.lib` | 1,873,052 | 1.786 | No | Ignored generated build/profiler output |
| `build/Release/tournament_tests.exe` | 1,082,368 | 1.032 | No | Ignored generated build/profiler output |
| `build/Release/TournamentCore.lib` | 1,312,706 | 1.252 | No | Ignored generated build/profiler output |
| `build-active/profile-asm/ChessAI_profile/HybridProfileStages.asm` | 3,484,592 | 3.323 | No | Ignored generated build/profiler output |
| `build-active/profile-asm/ChessAI_profile_reference/MLEvaluationV2.asm` | 6,660,540 | 6.352 | No | Ignored generated build/profiler output |
| `build-active/Release/ChessAI_tournament.exe` | 1,096,704 | 1.046 | No | Ignored generated build/profiler output |
| `build-active/Release/ChessCore.lib` | 1,869,720 | 1.783 | No | Ignored generated build/profiler output |
| `build-active/Release/ChessCoreDiagnostics.lib` | 1,873,152 | 1.786 | No | Ignored generated build/profiler output |
| `build-active/Release/tournament_tests.exe` | 1,082,368 | 1.032 | No | Ignored generated build/profiler output |
| `build-active/Release/TournamentCore.lib` | 1,312,730 | 1.252 | No | Ignored generated build/profiler output |
| `build-fallback/profile-asm/ChessAI_profile/HybridProfileStages.asm` | 3,484,592 | 3.323 | No | Ignored generated build/profiler output |
| `build-fallback/profile-asm/ChessAI_profile_reference/MLEvaluationV2.asm` | 6,660,540 | 6.352 | No | Ignored generated build/profiler output |
| `build-fallback/Release/ChessAI_tournament.exe` | 1,095,168 | 1.044 | No | Ignored generated build/profiler output |
| `build-fallback/Release/ChessCore.lib` | 1,861,268 | 1.775 | No | Ignored generated build/profiler output |
| `build-fallback/Release/ChessCoreDiagnostics.lib` | 1,864,694 | 1.778 | No | Ignored generated build/profiler output |
| `build-fallback/Release/tournament_tests.exe` | 1,080,832 | 1.031 | No | Ignored generated build/profiler output |
| `build-fallback/Release/TournamentCore.lib` | 1,312,734 | 1.252 | No | Ignored generated build/profiler output |
| `build-profile/profile-asm/ChessAI_profile/HybridProfileStages.asm` | 3,484,592 | 3.323 | No | Ignored generated build/profiler output |
| `build-profile/profile-asm/ChessAI_profile_reference/MLEvaluationV2.asm` | 6,660,540 | 6.352 | No | Ignored generated build/profiler output |
| `build-profile/Release/ChessAI_tournament.exe` | 1,096,704 | 1.046 | No | Ignored generated build/profiler output |
| `build-profile/Release/ChessCore.lib` | 1,869,732 | 1.783 | No | Ignored generated build/profiler output |
| `build-profile/Release/ChessCoreDiagnostics.lib` | 1,873,172 | 1.786 | No | Ignored generated build/profiler output |
| `build-profile/Release/tournament_tests.exe` | 1,082,368 | 1.032 | No | Ignored generated build/profiler output |
| `build-profile/Release/TournamentCore.lib` | 1,312,730 | 1.252 | No | Ignored generated build/profiler output |
| `build-tail/profile-asm/ChessAI_profile/HybridProfileStages.asm` | 3,484,592 | 3.323 | No | Ignored generated build/profiler output |
| `build-tail/profile-asm/ChessAI_profile_reference/MLEvaluationV2.asm` | 6,660,540 | 6.352 | No | Ignored generated build/profiler output |
| `build-tail/Release/ChessAI_tournament.exe` | 1,096,704 | 1.046 | No | Ignored generated build/profiler output |
| `build-tail/Release/ChessCore.lib` | 1,869,616 | 1.783 | No | Ignored generated build/profiler output |
| `build-tail/Release/ChessCoreDiagnostics.lib` | 1,873,064 | 1.786 | No | Ignored generated build/profiler output |
| `build-tail/Release/tournament_tests.exe` | 1,082,368 | 1.032 | No | Ignored generated build/profiler output |
| `build-tail/Release/TournamentCore.lib` | 1,312,722 | 1.252 | No | Ignored generated build/profiler output |
| `build-v2-validation/Release/ChessCore.lib` | 1,411,526 | 1.346 | No | Ignored generated build/profiler output |
| `ml/data/lichess_250k.npz` | 15,478,894 | 14.762 | No | Ignored raw/processed training data |
| `ml/data/lichess_250k_v2.npz` | 23,710,090 | 22.612 | No | Ignored raw/processed training data |
| `ml/data/lichess_db_eval.jsonl.zst` | 22,086,532,809 | 21,063.359 | No | Ignored raw/processed training data |
| `ml/models/smoke/MLWeights.h` | 2,054,177 | 1.959 | No | Ignored alternate model export |
| `ml/models/v1_export/MLWeights.h` | 2,057,526 | 1.962 | No | Ignored alternate model export |
| `ml/models/v2_preview/cpp/DirectWeightsV2.h` | 2,096,211 | 1.999 | No | Required deployed weights |
| `ml/models/v2_preview/cpp/ResidualWeightsV2.h` | 2,096,508 | 1.999 | No | Required deployed weights |
| `src/engine/generated/DirectWeightsV2.h` | 2,096,211 | 1.999 | Yes | Required deployed weights |
| `src/engine/generated/ResidualWeightsV2.h` | 2,096,508 | 1.999 | Yes | Required deployed weights |
| `stockfish/stockfish-windows-x86-64-universal.exe` | 103,046,300 | 98.273 | No | Ignored external Stockfish executable |

## E. Privacy/security and text findings

The whole-tree text scan recorded **23,855 matching lines** across
**1,684 decoded text files**, including source SVGs and dedication texts.
UTF-8/UTF-16 and CP1252 fallback covered generated profiler assembly/logs.
Compressed datasets, object files, images and other binary payloads were inventoried
and classified; they were not claimed to be plaintext-scanned. The complete line
catalogue contains relative file, line number, matched pattern types and inclusion
status; credential-like values are not copied into an audit report.

**SECURITY ISSUE: none identified, zero unresolved.** No credential-shaped GitHub
or API tokens, private-key markers, actual passwords/bearer secrets, personal email
addresses or private service URLs were found in publication candidates. Dependency
and vendor sources contain public contributor emails and security API vocabulary;
these are ignored rather than bundled. A keyword hit alone is not a credential.

**SAFE HISTORICAL PATHS:** the following records retain original local command and
data provenance. Thirteen benchmark records and two ML metadata files contain
user/institutional directory components; the validation status record contains
generic workstation/tool installation paths. They disclose local provenance,
not authentication information, and were preserved byte-for-byte.

| File | Matching lines | Category |
|---|---|---|
| `benchmarks/elo/validation_status.json` | 10 | SAFE HISTORICAL PATHS |
| `benchmarks/hybrid_profile_results.json` | 23, 25 | SAFE HISTORICAL PATHS |
| `benchmarks/optimization_abba_0.json` | 48, 50 | SAFE HISTORICAL PATHS |
| `benchmarks/optimization_abba_1.json` | 48, 50 | SAFE HISTORICAL PATHS |
| `benchmarks/optimization_abba_2.json` | 48, 50 | SAFE HISTORICAL PATHS |
| `benchmarks/optimization_abba_3.json` | 48, 50 | SAFE HISTORICAL PATHS |
| `benchmarks/optimization_baseline_performance.json` | 47, 49 | SAFE HISTORICAL PATHS |
| `benchmarks/optimization_baseline_profile.json` | 23, 25 | SAFE HISTORICAL PATHS |
| `benchmarks/optimization_candidates.json` | 18, 27 | SAFE HISTORICAL PATHS |
| `benchmarks/optimization_production_performance.json` | 50, 52 | SAFE HISTORICAL PATHS |
| `benchmarks/optimization_production_profile.json` | 24, 26 | SAFE HISTORICAL PATHS |
| `benchmarks/optimization_tail_performance.json` | 48, 50 | SAFE HISTORICAL PATHS |
| `benchmarks/optimization_tail_profile.json` | 24, 26 | SAFE HISTORICAL PATHS |
| `benchmarks/performance_results.json` | 47, 49 | SAFE HISTORICAL PATHS |
| `ml/data/lichess_250k.metadata.json` | 9 | SAFE HISTORICAL PATHS |
| `ml/data/lichess_250k_v2.metadata.json` | 9, 77 | SAFE HISTORICAL PATHS |

Other path hits are synthetic parser fixtures (`C:/some path/book`) or documented
compiler/tool install locations in historical protocols. Generated build logs,
CMake state, profiling output, virtual-environment configuration and old cleanup
scripts contain additional local paths; they are ignored. These are not required
machine paths for the public application.

**PRESENTATION ISSUE:** the old audit's missing-screenshot wording was stale and
has been replaced. No required public instruction embeds a user-specific path.
Secret-word false positives in candidates are UCI `token` parsing in
`benchmarks/elo/transport.py` (lines 57, 63, 158–166), the substring `sk-` in
`disk-backed` in `ml/preprocess_dataset.py` (line 1), and security vocabulary in
this audit. New SVG path-pattern hits are XML namespace URLs such as `xmlns:http...`,
which the broad drive-letter matcher also catches; they are not workstation paths.
None is a secret. No candidate email or private-key marker matched.

All 42 includable Python files parse. No candidate UTF-16, malformed characters,
merge markers or trailing-whitespace findings remain. Generated UTF-16 build
logs and assembly encoding differences are ignored. Frozen files were not
mechanically reformatted. The full TODO/debug/output line catalogue is retained
locally: runtime protocol `std::cout`, benchmark/progress prints, CLI/reporting,
regression diagnostics, temporary-directory handling and audit keyword descriptions
are legitimate. No accidental debugging output or unfinished feature placeholder
was identified in publication candidates.

## F. Third-party and license status

Both prior blockers are resolved. The root [LICENSE](../LICENSE) contains the
owner-selected MIT grant for ChessAI source and associated project documentation.
The twelve replacement PNGs use **Livius**, Martin Sedlák's original design from
[kmar/chess_svg_piece_sets](https://github.com/kmar/chess_svg_piece_sets), pinned to
`af40ea51e87eddee1ae7ee35ae312893a1271233`.

The author labels the sets cc0/public domain. The exact supplied license is a
[public-domain dedication](https://github.com/kmar/chess_svg_piece_sets/blob/af40ea51e87eddee1ae7ee35ae312893a1271233/livius/LICENSE),
explicitly permitting reproduction, distribution, modification and commercial use.
Its original text is retained at `src/gui/assets/pieces/livius/LICENSE`; it is not
misrepresented as standard CC0 1.0 legal code. Attribution is voluntary and provided.
Original SVGs, upstream README and SHA-256 mapping are bundled for provenance.
No proprietary Chess.com/Chess24 artwork is used.

Project MIT terms do not override third-party dedications/licenses. The window
icon and refreshed screenshots use the same public-domain pieces. Sounds remain
byte-identical code-generated WAVs; no fonts are bundled. Stockfish and separately
installed Python dependencies remain excluded. See
[third-party notices](../THIRD_PARTY_NOTICES.md).

## G. Screenshots and README

Both screenshots were recaptured from the real application after replacement and
visually inspected; no desktop/private data or fabricated values are present.
`gameplay.png`: 1454 × 880, 117,693 bytes.
`evaluator-selection.png`: 1454 × 880, 111,772 bytes.
All README image paths and all local Markdown links resolve. The MIT/license
notices are present and linked. Artwork now has verified redistribution terms.

Model `v2-residual-3fb0a29e8514af8c`, Hybrid alpha 0.25, 512 Stockfish 19 games
and 250 ms/move remain accurately documented. The observed crossing remains
1656.84, rounded to approximately 1657 UCI_Elo under the frozen protocol;
no universal/human rating is claimed. No frozen measurements were altered.

## H. Verification and preservation

Current verification passed:

- Actual GUI launch/event loop, clicks, legal targets, AI replies, move history,
  status, pending settings, evaluator choices, four original profiles, Random side,
  independent Flip Board and normal/minimum-size layouts.
- All twelve replacement sprites load and render, with Pillow and Tk-only fallback.
- All four promotion images have the correct color in both promotion modals;
  each of the eight choices selects correctly. All twelve render on the board.
- Actual Tk default test confirms production model ID and Hybrid alpha 0.25.
- Native CTest: all four groups passed again (perft/evaluation/tournament/openings).
- Every GUI class/function except asset loading has identical before/after AST.
  The existing piece-to-character mapping is unchanged.
- Of 207 protected files, only the authorized twelve PNGs and GUI asset-loader
  file differ. The other 194 files, including all engine/search/ML production
  source, deployed weights, CMake, tests and frozen evidence, are hash-identical.
- Before/after depth-3 moves, scores and node counts match for all 30 cases;
  static Classic, Direct/Residual V2, Hybrid and features match exactly.
- Rerun publication scan: 42 Python files parse, no candidate encoding/merge/
  trailing-whitespace findings, no unresolved security issues, no broken local
  links, no missing license/notices and no Git repository created.

The previous Release build and Python/evaluator parity tests remain valid with
unchanged native source/weights. No strength/calibration suite was rerun.
Local evidence is ignored under `build/pre-ship-audit/` and
`build/asset-replacement/`; conversion tooling in `build/asset-tools/` does not ship.

## I. Simulated first-add inclusion

**237 files** are included by the audited ignore rules: source/tests,
CMake/VERSION/launcher, MIT license and notices, documentation/real screenshots,
licensed PNGs and original SVG/dedication provenance, production headers/schema,
frozen benchmark evidence, ML workflows and selected small reproducibility JSON.
No Git initialization/staging/commit/tag/push was performed.

Exact candidate manifest:

```text
.gitignore
benchmarks/benchmark_performance.py
benchmarks/classic_vs_hybrid_32.json
benchmarks/classic_vs_hybrid_alpha_0.10_pilot.json
benchmarks/classic_vs_hybrid_alpha_0.25_pilot.json
benchmarks/classic_vs_hybrid_alpha_0.50_pilot.json
benchmarks/classic_vs_hybrid_alpha_0.75_pilot.json
benchmarks/classic_vs_hybrid_alpha_1.00_pilot.json
benchmarks/classic_vs_hybrid_depth3_32.json
benchmarks/classic_vs_ml_depth3_32.json
benchmarks/compare_v2_candidates.py
benchmarks/diagnose_evaluators.py
benchmarks/diagnostic_metrics.py
benchmarks/diagnostic_report.json
benchmarks/diagnostic_report.md
benchmarks/diagnostic_report.samples.jsonl
benchmarks/DIAGNOSTICS.md
benchmarks/elo/__init__.py
benchmarks/elo/calibrate.py
benchmarks/elo/calibration_protocol.json
benchmarks/elo/calibration_protocol.json.sha256
benchmarks/elo/calibration_stats.py
benchmarks/elo/create_openings_v1.py
benchmarks/elo/development_protocol.json
benchmarks/elo/development_protocol.json.sha256
benchmarks/elo/development_results.json
benchmarks/elo/development_results.md
benchmarks/elo/final_results.json
benchmarks/elo/final_results.md
benchmarks/elo/fixture_smoke_protocol.json
benchmarks/elo/fixture_smoke_protocol.json.sha256
benchmarks/elo/fixture_smoke_results.json
benchmarks/elo/fixture_smoke_results.md
benchmarks/elo/openings-v1.freeze.json
benchmarks/elo/openings-v1.tsv
benchmarks/elo/openings.py
benchmarks/elo/protocol.py
benchmarks/elo/README.md
benchmarks/elo/real_smoke_protocol.json
benchmarks/elo/real_smoke_protocol.json.sha256
benchmarks/elo/real_smoke_results.json
benchmarks/elo/real_smoke_results.md
benchmarks/elo/requirements.txt
benchmarks/elo/stockfish_detect.json
benchmarks/elo/transport.py
benchmarks/elo/validation_status.json
benchmarks/FINAL.md
benchmarks/final_v1_alpha025_250ms.json
benchmarks/final_v1_alpha025_depth3.json
benchmarks/HELDOUT.md
benchmarks/heldout_classic_vs_hybrid_alpha_0.10.json
benchmarks/heldout_classic_vs_hybrid_alpha_0.10_250ms.json
benchmarks/heldout_classic_vs_hybrid_alpha_0.25.json
benchmarks/heldout_classic_vs_hybrid_alpha_0.25_250ms.json
benchmarks/hybrid_profile_results.json
benchmarks/hybrid_profile_results.md
benchmarks/ml_vs_hybrid_depth3_32.json
benchmarks/optimization_abba_0.json
benchmarks/optimization_abba_0.md
benchmarks/optimization_abba_1.json
benchmarks/optimization_abba_1.md
benchmarks/optimization_abba_2.json
benchmarks/optimization_abba_2.md
benchmarks/optimization_abba_3.json
benchmarks/optimization_abba_3.md
benchmarks/optimization_baseline_performance.json
benchmarks/optimization_baseline_performance.md
benchmarks/optimization_baseline_profile.json
benchmarks/optimization_baseline_profile.md
benchmarks/optimization_candidates.json
benchmarks/optimization_candidates_parity.json
benchmarks/optimization_fallback_parity.json
benchmarks/optimization_integrity.json
benchmarks/optimization_production_parity.json
benchmarks/optimization_production_performance.json
benchmarks/optimization_production_performance.md
benchmarks/optimization_production_profile.json
benchmarks/optimization_production_profile.md
benchmarks/optimization_results.md
benchmarks/optimization_tail_parity.json
benchmarks/optimization_tail_performance.json
benchmarks/optimization_tail_performance.md
benchmarks/optimization_tail_profile.json
benchmarks/optimization_tail_profile.md
benchmarks/performance-middlegames-v1.tsv
benchmarks/PERFORMANCE.md
benchmarks/performance_results.json
benchmarks/performance_results.md
benchmarks/profile_hybrid.py
benchmarks/README.md
benchmarks/smoke_results.json
benchmarks/stockfish_labels.py
benchmarks/suites/common-openings-v1.tsv
benchmarks/suites/final-openings-v1.tsv
benchmarks/suites/heldout-openings-v1.tsv
benchmarks/summarize_v2_optimization.py
benchmarks/V2_OPTIMIZATION.md
CMakeLists.txt
docs/ARCHITECTURE.md
docs/BENCHMARKS.md
docs/images/evaluator-selection.png
docs/images/gameplay.png
docs/images/README.md
docs/ML_EVALUATION.md
docs/PUBLICATION_AUDIT.md
docs/RELEASE_AUDIT.md
docs/RELEASE_CHECK.md
LICENSE
ml/data/.gitkeep
ml/data/lichess_250k.metadata.json
ml/data/lichess_250k_v2.metadata.json
ml/export_model.py
ml/export_v2.py
ml/feature_schema_v2.json
ml/features.py
ml/features_v2.py
ml/generate_feature_schema.py
ml/make_example.py
ml/material_sanity.py
ml/model.py
ml/model_v2.py
ml/models/.gitkeep
ml/models/metrics.json
ml/models/v2_huber/comparison.json
ml/models/v2_huber/direct_history.json
ml/models/v2_huber/residual_history.json
ml/models/v2_mse/comparison.json
ml/models/v2_mse/direct_history.json
ml/models/v2_mse/residual_history.json
ml/prepare_v2.py
ml/preprocess_dataset.py
ml/README.md
ml/README_V2.md
ml/requirements.txt
ml/test_pipeline.py
ml/test_protocol.py
ml/train_evaluator.py
ml/train_v2.py
ml/V2_RESULTS.md
ml/verify_cpp.py
ml/verify_v2.py
README.md
run_chessai.bat
src/benchmark/CalibrationAdapter.cpp
src/benchmark/Diagnostics.cpp
src/benchmark/FinalOpenings.cpp
src/benchmark/HybridProfile.cpp
src/benchmark/HybridProfileStages.cpp
src/benchmark/HybridProfileStages.h
src/benchmark/main.cpp
src/benchmark/OpeningSuites.cpp
src/benchmark/Performance.cpp
src/benchmark/Tournament.cpp
src/benchmark/Tournament.h
src/chess/Board.cpp
src/chess/Board.h
src/chess/Move.cpp
src/chess/Move.h
src/chess/MoveGenerator.cpp
src/chess/MoveGenerator.h
src/chess/Types.h
src/engine/Engine.cpp
src/engine/Engine.h
src/engine/Evaluation.cpp
src/engine/Evaluation.h
src/engine/FeatureSchemaV2.h
src/engine/generated/.gitkeep
src/engine/generated/DirectWeightsV2.h
src/engine/generated/ResidualWeightsV2.h
src/engine/MLEvaluation.cpp
src/engine/MLEvaluation.h
src/engine/MLEvaluationV2.cpp
src/engine/MLEvaluationV2.h
src/engine/PositionEvaluator.cpp
src/engine/PositionEvaluator.h
src/engine/Search.cpp
src/engine/Search.h
src/engine/TranspositionTable.cpp
src/engine/TranspositionTable.h
src/engine/V2Kernels.cpp
src/engine/V2Kernels.h
src/engine/V2KernelsAVX2.cpp
src/engine/Zobrist.cpp
src/engine/Zobrist.h
src/game/Game.cpp
src/game/Game.h
src/game/GameController.cpp
src/game/GameController.h
src/gui/assets/pieces/bB.png
src/gui/assets/pieces/bK.png
src/gui/assets/pieces/bN.png
src/gui/assets/pieces/bP.png
src/gui/assets/pieces/bQ.png
src/gui/assets/pieces/bR.png
src/gui/assets/pieces/livius/bb.svg
src/gui/assets/pieces/livius/bk.svg
src/gui/assets/pieces/livius/bn.svg
src/gui/assets/pieces/livius/bp.svg
src/gui/assets/pieces/livius/bq.svg
src/gui/assets/pieces/livius/br.svg
src/gui/assets/pieces/livius/LICENSE
src/gui/assets/pieces/livius/provenance.json
src/gui/assets/pieces/livius/UPSTREAM_README.md
src/gui/assets/pieces/livius/wb.svg
src/gui/assets/pieces/livius/wk.svg
src/gui/assets/pieces/livius/wn.svg
src/gui/assets/pieces/livius/wp.svg
src/gui/assets/pieces/livius/wq.svg
src/gui/assets/pieces/livius/wr.svg
src/gui/assets/pieces/wB.png
src/gui/assets/pieces/wK.png
src/gui/assets/pieces/wN.png
src/gui/assets/pieces/wP.png
src/gui/assets/pieces/wQ.png
src/gui/assets/pieces/wR.png
src/gui/assets/sounds/capture.wav
src/gui/assets/sounds/check.wav
src/gui/assets/sounds/move.wav
src/gui/gui.py
src/main.cpp
tests/calibration_fixture_smoke.py
tests/calibration_tests.py
tests/diagnostic_tests.py
tests/eval_tool.cpp
tests/evaluation_tests.cpp
tests/fake_calibration_uci.py
tests/gui_defaults_test.py
tests/hybrid_profile_tests.py
tests/opening_suite_tests.cpp
tests/performance_tests.py
tests/perft_tests.cpp
tests/test_opening_manifests.py
tests/tournament_smoke.py
tests/tournament_tests.cpp
tests/verify_optimized_v2.py
THIRD_PARTY_NOTICES.md
VERSION
```

## J. Simulated first-add exclusion

Exclude `build/`, all `build-*/`, root `Testing/`, `.venv-elo/`, `stockfish/`,
bytecode/caches, IDE/local environment state, OS metadata, logs, profiler/temp
outputs, `README.txt` and `ml/generate_dataset.py`. Exclude every raw/NPZ dataset
except the explicitly retained metadata, and every checkpoint/alternate export/
training plot/log except `.gitkeep`, metrics and named comparison/history JSON.
No executable, generated build library, raw training dump or PyTorch checkpoint
is needed in the public source checkout. All benchmark final results/manifests/
protocols and runtime C++ headers remain included.

## K. Remaining blockers

None. The source license and artwork redistribution blockers are resolved.

## L. Final verdict

SHIP READY
