"""Isolated, overhead-calibrated reference stages and optimized Hybrid kernel controls."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import statistics
import subprocess
from benchmark_performance import write_atomic

STAGES = ("classic", "features", "linear1", "relu1", "linear2", "relu2", "output", "scale_add", "clip_round")


def summarize(rows):
    raw = [r for r in rows if r["type"] == "measurement"]
    def group(values):
        baseline = [r["elapsed_us"]/r["iterations"] for r in values if r["stage"] == "empty_control"]
        overhead = statistics.mean(baseline)
        result = {}
        for stage in sorted({r["stage"] for r in values}):
            samples = [r["elapsed_us"]/r["iterations"] for r in values if r["stage"] == stage]
            result[stage] = {"raw_us": statistics.mean(samples), "adjusted_us": statistics.mean(samples)-overhead,
                             "batch_std_us": statistics.pstdev(samples), "min_raw_us": min(samples), "max_raw_us": max(samples)}
        total = result["production_total"]["adjusted_us"]
        for stage in result:
            result[stage]["percent_of_production_total"] = 100*result[stage]["adjusted_us"]/total
        stage_sum = sum(result[s]["adjusted_us"] for s in STAGES)
        return {"timings": result, "empty_call_loop_us": overhead, "stage_sum_us": stage_sum,
                "stage_sum_percent_of_production": 100*stage_sum/total,
                "unattributed_or_decomposition_gap_us": total-stage_sum,
                "no_skip_slowdown": result["linear1_no_skip_control"]["adjusted_us"]/result["linear1"]["adjusted_us"]}
    return {"aggregate": group(raw), "per_position": {str(p): group([r for r in raw if r["position"] == p])
                                                    for p in sorted({r["position"] for r in raw})}}


def markdown(report):
    aggregate = report["summary"]["aggregate"]
    timings = aggregate["timings"]
    meta = report["metadata"]
    lines = ["# Hybrid V2 stage measurements", "", f"Model `{meta['model']}`, alpha {meta['alpha']}. {meta['build']}, {meta['compiler']}.",
             f"CPU: {report['cpu']}. {meta['positions']} fixed positions × {meta['repetitions']} repetitions; at least {meta['iterations']:,} calls per stage/position/repetition.",
             f"Adaptive batches are retimed until at least {meta['minimum_batch_us']} us; each row records its actual call count and duration. Discarded shorter attempts are not reported as measurements.",
             f"Warm-up: {meta['warmup']:,} calls before each batch. Bit-exact residual and integer Hybrid parity checked on {meta['parity_positions_including_children']} parents/legal children.", "",
             "Batched reference-stage decomposition, with separate optimized kernel controls. Percentages use the freshly measured production call, "
             "not a normalized stage sum. Empty-call/loop overhead is subtracted once per independently timed stage. "
             "Small stages and fusion/cache differences limit attribution; stage percentages need not sum to 100%.", "",
             "| Stage | Adjusted us/call | Raw us/call | % of production Hybrid | Across-batch std us |",
             "|---|---:|---:|---:|---:|"]
    for stage in STAGES:
        s = timings[stage]
        lines.append(f"| {stage} | {s['adjusted_us']:.6f} | {s['raw_us']:.6f} | {s['percent_of_production_total']:.3f}% | {s['batch_std_us']:.6f} |")
    lines += ["", f"Production total: **{timings['production_total']['adjusted_us']:.6f} us** adjusted; {timings['production_total']['raw_us']:.6f} us raw.",
              f"Stage sum: {aggregate['stage_sum_us']:.6f} us ({aggregate['stage_sum_percent_of_production']:.2f}% of production). "
              f"Signed attribution gap (production minus sum): {aggregate['unattributed_or_decomposition_gap_us']:+.6f} us.",
              f"Empty call/loop control: {aggregate['empty_call_loop_us']:.6f} us. Decomposed full pipeline: {timings['decomposed_total']['adjusted_us']:.6f} us.", "",
              "## Controls (not additional additive production stages)", "", "| Control | Adjusted us/call |", "|---|---:|"]
    for stage in ("fused_tail_control", "linear1_no_skip_control", "base_features_control", "feature_copy_setup_control", "plane_counts_control", "optimized_tail_control", "optimized_linear1_control", "active_list_linear1_control"):
        if stage not in timings: continue
        lines.append(f"| {stage} | {timings[stage]['adjusted_us']:.6f} |")
    lines += ["", f"Removing zero-input skipping made the first layer {aggregate['no_skip_slowdown']:.2f}x slower in the isolated control.",
              "", "## Per-position adjusted microseconds", "", "| Position | " + " | ".join(STAGES) + " | Production |", "|---|" + "---:|"*10]
    for position, stats in report["summary"]["per_position"].items():
        t = stats["timings"]
        lines.append("| " + report["positions"][int(position)]["id"] + " | " + " | ".join(f"{t[s]['adjusted_us']:.4f}" for s in (*STAGES, "production_total")) + " |")
    lines += ["", "Per-position percentages, batch variability, controls, sparsity and every raw measurement are retained in the JSON. "
              "See V2_OPTIMIZATION.md for implementation, compiler evidence and parity results.", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", type=Path, default=Path("build-profile/Release/ChessAI_profile.exe"))
    parser.add_argument("--positions", type=Path, default=Path("benchmarks/performance-middlegames-v1.tsv"))
    parser.add_argument("--iterations", type=int, default=50000)
    parser.add_argument("--repetitions", type=int, default=5)
    parser.add_argument("--warmup", type=int, default=2000)
    parser.add_argument("--output", type=Path, default=Path("benchmarks/hybrid_profile_results.json"))
    args = parser.parse_args()
    if args.output.exists() or args.output.with_suffix(".md").exists():
        parser.error("Choose a fresh output path; existing reports are preserved")
    if min(args.iterations, args.repetitions, args.warmup) < 1:
        parser.error("Counts must be positive")
    command = [str(args.engine.resolve()), "--positions", str(args.positions.resolve()), "--iterations", str(args.iterations),
               "--repetitions", str(args.repetitions), "--warmup", str(args.warmup)]
    cpu = platform.processor()
    if platform.system() == "Windows":
        cpu = subprocess.check_output(["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_Processor).Name"], text=True).strip()
    start = datetime.now(timezone.utc).isoformat()
    process = subprocess.Popen(command, stdout=subprocess.PIPE, text=True)
    try:
        stdout, _ = process.communicate()
        if process.returncode: raise RuntimeError("Native profile failed; no results published")
    except BaseException:
        process.kill(); process.wait(); raise
    rows = [json.loads(line) for line in stdout.splitlines()]
    if rows[-1]["type"] != "complete": raise RuntimeError("Incomplete profile")
    positions = []
    for line in args.positions.read_text().splitlines()[1:]:
        name, fen = line.split("\t")
        positions.append({"id": name, "fen": fen})
    report = {"format_version": 1, "purpose": "isolated profiling and kernel comparison; no strength experiment", "started_utc": start,
              "finished_utc": datetime.now(timezone.utc).isoformat(), "cpu": cpu, "platform": platform.platform(),
              "metadata": rows[0], "command": command, "positions": positions,
              "manifest_sha256": hashlib.sha256(args.positions.read_bytes()).hexdigest(),
              "executable_sha256": hashlib.sha256(args.engine.read_bytes()).hexdigest(),
              "summary": summarize(rows), "sparsity": [r for r in rows if r["type"] == "sparsity"],
              "raw_measurements": [r for r in rows if r["type"] == "measurement"]}
    write_atomic(args.output, json.dumps(report, indent=2, allow_nan=False)+"\n")
    write_atomic(args.output.with_suffix(".md"), markdown(report))
    print(f"Saved {args.output} and {args.output.with_suffix('.md')}")


if __name__ == "__main__":
    main()
