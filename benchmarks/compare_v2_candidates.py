"""Rotate complete evaluator candidates and kernel controls in the same native run."""
import argparse
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
from benchmark_performance import write_atomic

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--engine', type=Path, default=Path('build-tail/Release/ChessAI_profile.exe'))
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
if args.output.exists(): parser.error('Choose a new output path')
manifest = Path('benchmarks/performance-middlegames-v1.tsv')
command = [str(args.engine.resolve()), '--compare-candidates', '--iterations', '50000',
           '--repetitions', '5', '--warmup', '2000', '--positions', str(manifest.resolve())]
process = subprocess.Popen(command, stdout=subprocess.PIPE, text=True)
try:
    stdout, _ = process.communicate()
    if process.returncode: raise RuntimeError('Candidate measurement failed')
except BaseException:
    process.kill(); process.wait(); raise
rows = [json.loads(line) for line in stdout.splitlines()]
assert rows[-1]['type'] == 'complete'
measurements = [r for r in rows if r['type'] == 'measurement']
overhead = statistics.mean(r['elapsed_us']/r['iterations'] for r in measurements if r['stage'] == 'empty_control')
summary = {}
for stage in sorted({r['stage'] for r in measurements}):
    values = [r['elapsed_us']/r['iterations'] for r in measurements if r['stage'] == stage]
    summary[stage] = {'raw_us': statistics.mean(values), 'adjusted_us': statistics.mean(values)-overhead,
                      'batch_std_us': statistics.pstdev(values)}
report = {'metadata': rows[0], 'command': command, 'timings': summary, 'raw_rows': rows,
          'executable_sha256': hashlib.sha256(args.engine.read_bytes()).hexdigest(),
          'manifest_sha256': hashlib.sha256(manifest.read_bytes()).hexdigest(),
          'note': 'Complete candidate totals include features, Classic, alpha, clipping and rounding. '
                  'Explicit backend wrappers omit production mode dispatch; production_total retains it. '
                  'List construction is included in active-list kernel/total times; standalone construction is an isolated control.'}
write_atomic(args.output, json.dumps(report, indent=2)+'\n')
print(json.dumps(summary, indent=2))
