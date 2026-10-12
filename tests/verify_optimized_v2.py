"""Full-corpus bitwise residual and integer Hybrid comparison; no strength games."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import numpy as np

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--tool', type=Path, required=True)
parser.add_argument('--data', type=Path, default=Path('ml/data/lichess_250k_v2.npz'))
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--require-avx2', action='store_true')
args = parser.parse_args()
if args.output.exists():
    parser.error('Choose a new output path')
with np.load(args.data) as data:
    fens = data['fen']
    text = '\n'.join(str(fen) + (' 0 1' if len(str(fen).split()) == 4 else '') for fen in fens) + '\n'
result = subprocess.run([str(args.tool.resolve()), 'compare-residual'], input=text, text=True,
                        capture_output=True, check=True)
report = json.loads(result.stdout)
assert report['positions'] == len(fens)
if args.require_avx2:
    assert report['avx2_active'], 'Test did not exercise AVX2'
for backend in report['backends']:
    assert backend['exact_residual_matches'] == len(fens)
    assert backend['integer_hybrid_changes'] == 0
report['dataset_sha256'] = hashlib.sha256(args.data.read_bytes()).hexdigest()
report['executable_sha256'] = hashlib.sha256(args.tool.read_bytes()).hexdigest()
args.output.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
