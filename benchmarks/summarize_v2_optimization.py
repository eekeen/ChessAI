"""Assemble the completed, preserved V2 inference measurements without rerunning them."""
import json
from pathlib import Path
import statistics
from benchmark_performance import write_atomic

root = Path(__file__).resolve().parent
def load(name):
    return json.loads((root / name).read_text())
base_profile = load('optimization_baseline_profile.json')['summary']['aggregate']['timings']
tail_profile = load('optimization_tail_profile.json')['summary']['aggregate']['timings']
prod_profile = load('optimization_production_profile.json')['summary']['aggregate']['timings']
comparison = load('optimization_candidates.json')['timings']
before = load('optimization_baseline_performance.json')['summary']
after = load('optimization_production_performance.json')['summary']
baseline = base_profile['production_total']['adjusted_us']
production = prod_profile['production_total']['adjusted_us']
us = lambda stage: comparison[stage]['adjusted_us']
candidates = [
    ('Reference (shared run)', 'reference_total', 'linear1', 'fused_tail_control'),
    ('Tail only', 'tail_total', 'linear1', 'optimized_tail_control'),
    ('AVX2 scan Linear1 only', 'sparse_only_total', 'optimized_linear1_control', 'fused_tail_control'),
    ('Active-list Linear1 only', 'active_only_total', 'active_list_linear1_control', 'fused_tail_control'),
    ('Tail + AVX2 scan Linear1', 'sparse_total', 'optimized_linear1_control', 'optimized_tail_control'),
    ('Tail + active-list Linear1', 'active_total', 'active_list_linear1_control', 'optimized_tail_control'),
]
lines = ['# Measured V2 inference optimization', '',
         'Model `v2-residual-3fb0a29e8514af8c`, alpha **0.25**. Ryzen 7 3700X, MSVC 19.28, Release.',
         'Selected production implementation: **AVX2 fused tail + active-index sparse Linear1**.', '',
         f'Fresh reference profile: {baseline:.6f} us/evaluation. Final production: **{production:.6f} us/evaluation**, '
         f'**{baseline/production:.3f}x throughput**, **{100*(1-production/baseline):.2f}% less latency**.', '',
         '## Same-run candidate comparison', '',
         'All complete candidates rotated within the same run: 16 positions, five repetitions, 50,000 calls and 2,000 warm-up calls. '
         'Totals include features, Classic, residual scaling, clipping and rounding. Explicit-backend wrappers omit only mode dispatch. '
         'Eval/s is the reciprocal of adjusted latency. Speedup below means latency reduction versus the requested fresh reference baseline.', '',
         '| Implementation | Hybrid us/eval | eval/s | Linear1 us | Tail us | Speedup vs fresh reference |',
         '|---|---:|---:|---:|---:|---:|']
for label, total, linear, tail in candidates:
    value = us(total)
    lines.append(f'| {label} | {value:.3f} | {1e6/value:,.0f} | {us(linear):.3f} | {us(tail):.3f} | {100*(1-value/baseline):+.2f}% |')
lines += ['', f'The same-run reference measured {us("reference_total"):.3f} us versus the earlier {baseline:.3f} us, '
          'showing run-to-run variation. Candidate ranking uses same-run comparisons and the alternating production-entry check below. '
          'The reference Linear1 control is an isolated scalar profiling copy; original production Linear1 receives SSE code generation. '
          'Do not sum isolated stage controls or mistake their ratio for end-to-end acceleration.', '',
          f'Common controls in this run: features **{us("features"):.6f} us**; reference Linear1 **{us("linear1"):.6f} us**; '
          f'AVX2 scan Linear1 **{us("optimized_linear1_control"):.6f} us**; active-list Linear1 **{us("active_list_linear1_control"):.6f} us**; '
          f'reference tail **{us("fused_tail_control"):.6f} us**; optimized tail **{us("optimized_tail_control"):.6f} us**.',
          f'Isolated active-list construction: **{us("list_construction_control"):.6f} us**. '
          'Construction is already included in active-list kernel and total timings; it is not subtracted or added again. '
          'Feature extraction is unchanged for every candidate. Average active features: **38.375 / 789**.', '',
          'The AVX2 scan is rejected: it loses end-to-end to the existing SSE path. '
          'Active-list-only is not deployed; its small gain against the same-run reference does not beat the earlier fresh baseline. '
          'Only the combined tail/active-list winner is selected.']
abba = [load(f'optimization_abba_{i}.json')['summary']['static']['hybrid']['average_latency_us'] for i in range(4)]
tail_mean, active_mean = statistics.mean((abba[0], abba[3])), statistics.mean((abba[1], abba[2]))
lines += ['', '## Production-entry confirmation', '',
          f'Alternating tail/active/active/tail runs measured {", ".join(f"{v:.6f}" for v in abba)} us respectively. '
          f'Tail mean **{tail_mean:.6f} us**; active-list mean **{active_mean:.6f} us**: '
          f'**{100*(1-active_mean/tail_mean):.2f}% less latency** including construction and actual production dispatch. '
          'Each run used the same 16 round-robin positions, three 200,000-evaluation repetitions and 10,000 warm-up evaluations. '
          'The 1 ms search smoke accompanying these static runs is not used to select an implementation.', '',
          '## Final production versus fresh reference', '',
          '| Measurement | Reference | Tail only | Selected production |', '|---|---:|---:|---:|']
for label, key in [('Profile Hybrid us', 'production_total'), ('Feature extraction us', 'features')]:
    lines.append(f'| {label} | {base_profile[key]["adjusted_us"]:.6f} | {tail_profile[key]["adjusted_us"]:.6f} | {prod_profile[key]["adjusted_us"]:.6f} |')
lines += [f'| Selected Linear1 control us | {base_profile["linear1"]["adjusted_us"]:.6f} | {tail_profile["linear1"]["adjusted_us"]:.6f} | {prod_profile["active_list_linear1_control"]["adjusted_us"]:.6f} |',
          f'| Selected tail control us | {base_profile["fused_tail_control"]["adjusted_us"]:.6f} | {tail_profile["optimized_tail_control"]["adjusted_us"]:.6f} | {prod_profile["optimized_tail_control"]["adjusted_us"]:.6f} |', '']
b, a = before['static']['hybrid'], after['static']['hybrid']
lines += [f'Round-robin production benchmark: **{b["average_latency_us"]:.6f} → {a["average_latency_us"]:.6f} us**, '
          f'**{b["evaluations_per_second"]:,.0f} → {a["evaluations_per_second"]:,.0f} eval/s** '
          f'({100*(a["evaluations_per_second"]/b["evaluations_per_second"]-1):.2f}% higher throughput; '
          f'{100*(1-a["average_latency_us"]/b["average_latency_us"]):.2f}% lower latency). '
          'These round-robin timings have different cache behavior from repeated-position profiling.', '',
          '## Search, unchanged settings', '',
          '| Budget | Nodes/s before → after | Improvement | Mean completed depth before → after | Total nodes before → after |',
          '|---|---:|---:|---:|---:|']
for budget in ('100', '250', '1000'):
    b, a = before['search'][budget]['hybrid'], after['search'][budget]['hybrid']
    lines.append(f'| {budget} ms | {b["nodes_per_second"]:,.0f} → {a["nodes_per_second"]:,.0f} | '
                 f'{100*(a["nodes_per_second"]/b["nodes_per_second"]-1):+.2f}% | '
                 f'{b["completed_depth"]["mean"]:.3f} → {a["completed_depth"]["mean"]:.3f} | '
                 f'{b["total_nodes"]:,} → {a["total_nodes"]:,} |')
lines += ['', 'Three repetitions on all 16 positions at each budget, identical search code/settings and cleared TT. '
          'Timed depth is a performance observation, not strength evidence.', '',
          'The earlier tail-only run also had faster unchanged Classic searches (124,936 nodes/s at 1000 ms, '
          'versus 105,869 in the final run and 105,210 in the fresh baseline). Separate tail/final search runs '
          'do not establish the active-list component\'s incremental search gain. Selection uses same-run '
          'complete-evaluator and alternating production static measurements.', '',
          '## Correctness and attribution', '',
          '**250,000/250,000 production residuals bit-identical; max/mean difference 0 cp; zero rounded Hybrid score changes.** '
          'All explicit candidates also pass. Python/C++ parity, profiler parity, native perft/evaluation/search/game-rule/tournament/opening tests, '
          'tournament overrides, frozen manifests, protocol, diagnostics, GUI defaults and ML pipeline tests pass.', '',
          'All 25 protected artifacts retain their hashes. Original forward and feature bodies are unchanged. '
          'All 48 fixed-depth search cases match the reference in scores, moves and node counts '
          '(16 performance positions, three evaluators, depth 3, alpha 0.25). See optimization_integrity.json.', '',
          'The AVX2-disabled fallback build passes all 250,000 positions, profiler parity and all four native test groups. '
          'Runtime CPU/OS checks preserve this reference path on unsupported CPUs. A physical non-AVX2 CPU was not available.', '',
          'The **fused tail is the largest contributor**: tail-only reduced the fresh profile from '
          f'{baseline:.3f} to {tail_profile["production_total"]["adjusted_us"]:.3f} us. '
          'Active-index Linear1 supplies the smaller additional measured gain. '
          'No features, weights, alpha, search settings or frozen strength suites/results changed. No final strength matches ran.', '',
          'Implementation, compiler flags, exact commands and validation details: [V2_OPTIMIZATION.md](V2_OPTIMIZATION.md). '
          'Raw per-position/per-repetition measurements are preserved in the matching `optimization_*.json` reports.', '']
destination = root / 'optimization_results.md'
if destination.exists(): raise SystemExit('Preserve the existing report; choose a fresh destination')
write_atomic(destination, '\n'.join(lines))
print(destination)
