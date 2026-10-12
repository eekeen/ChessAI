# V2 residual inference optimization

See [the measured comparison and final search results](optimization_results.md)
for all candidates, production latency/throughput, node counts and completed depths.

The model `v2-residual-3fb0a29e8514af8c`, weights, 789 feature semantics,
Hybrid alpha 0.25, clipping, rounding and search settings remain fixed.
No strength results inform kernel selection. Frozen strength suites and reports
are preserved; these experiments use only `performance-middlegames-v1.tsv`.

## Implementations and safety

`MLEvaluationV2.cpp` retains the original `forward` implementation as reference.
Direct ML continues using it. Explicit verification backends select reference,
optimized tail, optimized tail plus sparse Linear1, or an active-index experiment.
The CMake cache setting `CHESSAI_V2_OPTIMIZATION` selects reference (0), tail (1),
tail plus sparse Linear1 (2), or tail plus active-index Linear1 (3). Candidate builds are isolated from the normal build
until correctness and performance checks pass.

Production now defaults to **3**, the measured tail plus active-index winner.
Mode 2 is retained only as an explicit verification/benchmark choice; it is not
selected automatically. Runtime dispatch selects only the winning implementation
or the reference fallback. The existing kernels were not rewritten during the
continuation of this experiment.

`V2KernelsAVX2.cpp` alone receives `/arch:AVX2 /fp:strict` under MSVC x64.
Other sources retain `/O2 /Ob2 /DNDEBUG` and the existing floating-point settings.
The baseline-ISA dispatcher checks AVX, OSXSAVE, XCR0 XMM/YMM state and AVX2.
Unsupported processors, other toolchains and `CHESSAI_V2_ENABLE_AVX2=OFF`
use the portable original reference. There are no AVX static constructors.

The fused tail packs W2 once into aligned `[8 blocks][128 inputs][8 neurons]`
storage, copying every original float exactly. SIMD lanes represent independent
neurons. Each neuron receives its 128 products in the original order; output
weights and ReLU are consumed in original neuron order. There is no horizontal
reduction, reassociation or FMA. An eight-float temporary replaces a full second
layer activation buffer. Thread-safe packing occurs on first use, before timed
batches because benchmarks warm up.

MSVC 19.28 disassembly of the Release kernel object contains `vmulps` and `vaddps`,
and `vzeroupper` at the AVX/SSE boundary, with no fused multiply-add instructions.
The previous implementation used `mulps/addps` in Linear1 and scalar
`mulss/addss` in the tail. Broad `/fp:fast` or global `/arch:AVX2` is not enabled.

Sparse Linear1 retains ascending feature order and zero skipping. AVX2 updates
eight independent outputs at a time using unaligned loads (generated W1 need not
be 32-byte aligned). Feature extraction and its temporary arrays are unchanged.
An alternative first builds ascending nonzero indices and then accumulates only
those rows; its list-construction cost is included in the measured control.
It does not change production feature extraction or specialize binary features.

`compare_v2_candidates.py` runs all complete candidates in the same rotating
native experiment (16 positions, 50,000 calls, five repetitions, 2,000 warm-up).
It also tests Linear1-only replacements with the original scalar tail to separate
individual gains from combined gains. These explicit-backend wrappers include the
whole Hybrid calculation but omit the mode dispatch of `PositionEvaluator`.
`production_total` keeps the actual dispatch; a full production benchmark confirms
the winner. Candidate controls include list construction, so its cost is not
subtracted to make the active-list approach look faster. A separate list control
estimates construction alone; it is not an exact additive decomposition.

## Measurement interpretation

The nine original profiling stages remain reference controls; newly added
`optimized_tail_control`, `optimized_linear1_control` and
`active_list_linear1_control` call the actual dispatch/kernel implementation.
`production_total` measures the selected complete evaluator. Stage percentages
use that total as denominator and are not additive attribution: isolated loops,
fusion and cache state affect code generation. In particular MSVC vectorizes the
original production Linear1 inner loop with SSE, while its isolated profiling
copy was not vectorized. Use full evaluator throughput for acceptance.

Profiles repeat each position/stage 50,000 times, five repetitions, 2,000 warm-up
calls. End-to-end measurements use 200,000 evaluations per batch, three repetitions,
10,000 warm-up evaluations and all 16 positions at 100/250/1000 ms search budgets.
No concurrent compilation or tests are run during the performance acceptance runs.
Timed search depth can vary because the faster evaluator visits more nodes within
the unchanged deadline; this is not a change to search settings or evaluator scores.

## Reproduction

```powershell
cmake -S . -B build-reference -A x64 -DCHESSAI_BUILD_PROFILER=ON -DCHESSAI_V2_OPTIMIZATION=0
cmake --build build-reference --config Release
cmake -S . -B build-tail -A x64 -DCHESSAI_BUILD_PROFILER=ON -DCHESSAI_V2_OPTIMIZATION=1
cmake --build build-tail --config Release
cmake -S . -B build-optimized -A x64 -DCHESSAI_BUILD_PROFILER=ON -DCHESSAI_V2_OPTIMIZATION=2
cmake --build build-optimized --config Release
python tests/verify_optimized_v2.py --tool build-optimized/Release/eval_tool.exe --require-avx2 --output benchmarks/new_parity.json
python benchmarks/profile_hybrid.py --engine build-optimized/Release/ChessAI_profile.exe --iterations 50000 --repetitions 5 --warmup 2000 --output benchmarks/new_profile.json
python benchmarks/benchmark_performance.py --engine build-optimized/Release/ChessAI_performance.exe --repetitions 3 --evaluations 200000 --warmup 10000 --budgets 100,250,1000 --output benchmarks/new_performance.json
```

The commands above retain the simple sparse candidate for reproducibility. Build
the selected production path with:

```powershell
cmake -S . -B build -DCHESSAI_V2_OPTIMIZATION=3
cmake --build build --config Release
cmake -S . -B build-profile -DCHESSAI_BUILD_PROFILER=ON -DCHESSAI_V2_OPTIMIZATION=3
cmake --build build-profile --config Release
python tests/verify_optimized_v2.py --tool build/Release/eval_tool.exe --require-avx2 --output benchmarks/new_production_parity.json
python benchmarks/profile_hybrid.py --iterations 50000 --repetitions 5 --warmup 2000 --output benchmarks/new_production_profile.json
python benchmarks/benchmark_performance.py --repetitions 3 --evaluations 200000 --warmup 10000 --budgets 100,250,1000 --output benchmarks/new_production_performance.json
```

An existing CMake cache can retain a previous backend, so pass `=3` explicitly
when updating an existing build. Fresh builds default to 3. On this workstation,
CMake is installed at
`C:/Program Files (x86)/Microsoft Visual Studio/2019/Community/Common7/IDE/CommonExtensions/Microsoft/CMake/CMake/bin/cmake.exe`.

Use fresh output filenames; wrappers preserve previous reports. Run the same
commands against the reference and tail builds for comparison. All-corpus parity
checks every row of the existing 250,000-position NPZ, reports bit-exact matches,
max/mean residual differences and final integer Hybrid changes for each candidate.
It fails on any mismatch and records dataset/executable hashes. The profiler also
checks reference/optimized layer outputs on 634 benchmark parents and legal children.

## Correctness and fallback gates

After the production switch, all 250,000 production residuals matched the original
reference bit-for-bit (maximum and mean difference 0 cp); no rounded Hybrid score
changed. The test checks both `MLEvaluationV2::predict` and the actual
`PositionEvaluator::evaluate` production path, in addition to all explicit candidates.
Python/C++ feature parity is exact across 264 positions; existing PyTorch inference
errors remain 0.001342 cp Direct and 0.001464 cp residual, unchanged from reference.
Python and C++ were not bit-identical before optimization; the optimized C++ path
is bit-identical to the original C++ path.

Passed after switching: all four native CTest groups (perft, evaluation/search/game
rules, tournament, opening suites), three profiler tests including the 20-iteration
positive-duration smoke, tournament override tests, two frozen manifest tests,
eight diagnostic tests, two performance tests, actual Tk GUI defaults, engine
protocol and six ML pipeline tests. No model training or final-suite matches ran.
All 25 protected artifact hashes match the pre-optimization snapshot, and both
the original `forward` body and feature extraction body are unchanged. The 48
fixed-depth search comparisons (16 performance positions × three evaluators,
depth 3, alpha 0.25) match in scores, best moves and node counts against fallback.

The isolated `build-fallback` used optimization=3 with AVX2 compilation disabled.
All 250,000 positions matched exactly for every candidate, the profiler parity
passed, and all four native test groups passed. This exercises the same reference
fallback selected when runtime support is absent, without linking the AVX2 TU.
Runtime guards were inspected; this host supports AVX2, so execution on physical
non-AVX2 hardware was not available for testing. Other toolchains use the portable
path rather than assuming this MSVC-specific kernel build is supported.
