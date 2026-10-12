# v1.0.0 repository audit

This is the earlier release-preparation record. See the
[2026-10-12 publication audit](PUBLICATION_AUDIT.md) for the current final review,
additional retained research metadata/metrics and remaining publication blockers.
The previous image-rights blocker has been resolved with public-domain Livius
artwork; the source is now MIT licensed. The current audit records verification.

Release preparation changes presentation and packaging only. No engine, search, weights, alpha, timing, kernels, tests or frozen artifacts were edited. No files were deleted. This working folder had no Git repository; no history, commit, tag or push was created.

## Inclusion decisions

| Content | Decision |
|---|---|
| `src/`, `tests/`, CMake and feature schemas | Include |
| `src/engine/generated/DirectWeightsV2.h`, `ResidualWeightsV2.h` | Include: approximately 4 MiB of deployed weights; previously ignored incorrectly |
| GUI PNG/WAV assets | Include; preserve existing behavior and offline availability |
| Benchmark summaries, JSON results, TSV suites, manifests, protocols and calibration reports | Include; remove previous blanket `benchmarks/*.json` exclusion |
| `build/`, `build-*/`, `Testing/`, compiled binaries and IDE state | Ignore |
| `.venv*`, Python caches, logs, temporary files and local environment files | Ignore |
| `ml/data/` | Ignore roughly 21,101 MiB of raw/processed data; retain `.gitkeep` if present |
| `ml/models/` | Ignore roughly 11.62 MiB of checkpoints, training logs, plots and alternate exports; deployed headers are outside this directory |
| `stockfish/` | Ignore the roughly 99.74 MiB downloaded third-party engine distribution; users install separately |
| `benchmarks/local/`, root `benchmark_results.json` | Ignore ad-hoc future outputs |

Existing benchmark evidence is approximately 32.59 MiB, including the 18 MB final external game record. It is intentionally retained for review and reproducibility. Local performance, smoke and development artifacts remain distinguishable from frozen final results. No blanket JSON/TSV/image exclusion is used.

## Publication review

Thirteen benchmark files contain historical absolute user paths, including profiler/optimization provenance. Frozen reports and protocol metadata were left byte-for-byte intact as requested. New release documentation and the launcher use repository-relative or generic commands. Inspect historical provenance before public publication; removing it would require a separately authorized archival/redaction decision.

At the earlier review, LICENSE and image provenance were unresolved. Both are now
resolved: ChessAI source is MIT licensed, and the twelve piece PNGs use Martin
Sedl?k's public-domain Livius set. See the current publication audit and
THIRD_PARTY_NOTICES.md for the exact upstream dedication and revision. Stockfish
remains excluded rather than repackaged.

`README.txt` was empty and remains untouched; `README.md` is the canonical entry point. Older guides and reports preserve their historical context, including pre-result language and local tool-installation examples. New release guides link completed results explicitly.

## Verification

Git ignore semantics were tested in a temporary isolated repository with 18 include/exclude cases. Production headers, final results, frozen protocols, schema and GUI images remain includable. A pre-edit SHA-256 snapshot covers 197 source, test, ML-workflow and benchmark files plus CMake; every protected file remained unchanged. See [release checks](RELEASE_CHECK.md).
