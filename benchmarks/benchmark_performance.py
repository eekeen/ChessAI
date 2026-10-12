"""Run native production-evaluator performance measurements, not strength matches."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import tempfile

MODES = ("classic", "ml", "hybrid")


def stats(values):
    return {"mean": statistics.mean(values), "std": statistics.pstdev(values),
            "min": min(values), "max": max(values)}


def summarize(rows):
    micro, searches = {}, {}
    for mode in MODES:
        batch = [r for r in rows if r["type"] == "static" and r["mode"] == mode]
        count, elapsed = sum(r["evaluations"] for r in batch), sum(r["elapsed_ms"] for r in batch)
        micro[mode] = {"evaluations": count, "elapsed_ms": elapsed, "evaluations_per_second": 1000*count/elapsed,
                       "average_latency_us": 1000*elapsed/count,
                       "batch_latency_us": stats([1000*r["elapsed_ms"]/r["evaluations"] for r in batch])}
    for mode in MODES:
        micro[mode]["slowdown_vs_classic"] = micro[mode]["average_latency_us"] / micro["classic"]["average_latency_us"]
    budgets = sorted({r["budget_ms"] for r in rows if r["type"] == "search"})
    def group_summary(group):
        nodes, elapsed = sum(r["nodes"] for r in group), sum(r["elapsed_ms"] for r in group)
        return {"samples": len(group), "total_nodes": nodes, "elapsed_ms": elapsed,
                "nodes_per_second": 1000*nodes/elapsed, "tt_hits": sum(r["tt_hits"] for r in group),
                "completed_depth": stats([r["completed_depth"] for r in group]),
                "nodes": stats([r["nodes"] for r in group]),
                "sample_nodes_per_second": stats([1000*r["nodes"]/r["elapsed_ms"] for r in group]),
                "sample_elapsed_ms": stats([r["elapsed_ms"] for r in group]),
                "mate_early_stops": sum(abs(r["score"]) >= 99000 for r in group)}
    for budget in budgets:
        searches[str(budget)] = {}
        for mode in MODES:
            group = [r for r in rows if r["type"] == "search" and r["budget_ms"] == budget and r["mode"] == mode]
            searches[str(budget)][mode] = {**group_summary(group), "per_position": {
                str(p): group_summary([r for r in group if r["position"] == p]) for p in sorted({r["position"] for r in group})}}
        classic_depth = searches[str(budget)]["classic"]["completed_depth"]["mean"]
        for mode in MODES:
            searches[str(budget)][mode]["average_depth_difference_vs_classic"] = searches[str(budget)][mode]["completed_depth"]["mean"]-classic_depth
    return {"static": micro, "search": searches}


def write_atomic(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def markdown(report):
    meta = report["native_metadata"]
    lines = ["# Measured evaluator performance", "", "Performance only; these are not playing-strength results.", "",
             f"Machine: {report['machine']['cpu']}; {report['machine']['platform']}. Build: {meta['build_type']}, {meta['compiler']}.",
             f"Hybrid alpha: {meta['hybrid_alpha']}; model: `{meta['models']['hybrid']}`.",
             f"Manifest: `{meta['manifest_version']}`, SHA-256 `{report['manifest_sha256']}`.",
             f"{meta['positions']} positions, {meta['repetitions']} repetitions; one search thread. UTC: {report['started_utc']}.", "",
             "## Static evaluation", "", "| Evaluator | Evaluations/sec | Average latency us | Batch latency std us | Slowdown |",
             "|---|---:|---:|---:|---:|"]
    for mode, m in report["summary"]["static"].items():
        lines.append(f"| {mode} | {m['evaluations_per_second']:,.0f} | {m['average_latency_us']:.3f} | {m['batch_latency_us']['std']:.3f} | {m['slowdown_vs_classic']:.2f}x |")
    lines += ["", "## Search at equal wall-clock budgets", "", "| Budget ms | Evaluator | Avg completed depth | Depth delta vs Classic | Avg nodes | Nodes/sec | Total nodes | TT hits | Elapsed s |",
              "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    for budget, modes in report["summary"]["search"].items():
        for mode, m in modes.items():
            lines.append(f"| {budget} | {mode} | {m['completed_depth']['mean']:.3f} | {m['average_depth_difference_vs_classic']:+.3f} | {m['nodes']['mean']:,.0f} | {m['nodes_per_second']:,.0f} | {m['total_nodes']:,} | {m['tt_hits']:,} | {m['elapsed_ms']/1000:.3f} |")
    lines += ["", "## Per-position completed depths", "", "Each cell: mean [min–max] across repetitions. Raw nodes, elapsed time, TT hits and moves are in JSON.", "",
              "| Budget ms | Position | Classic | ML | Hybrid |", "|---|---|---:|---:|---:|"]
    for budget, modes in report["summary"]["search"].items():
        for position in report["positions"]:
            cells = []
            for mode in MODES:
                d = modes[mode]["per_position"][str(position["index"])]["completed_depth"]
                cells.append(f"{d['mean']:.2f} [{d['min']}–{d['max']}]")
            lines.append(f"| {budget} | {position['id']} | " + " | ".join(cells) + " |")
    hybrid_static = report["summary"]["static"]["hybrid"]
    lines += ["", "## Interpretation", "",
              f"Hybrid static evaluation took {hybrid_static['slowdown_vs_classic']:.2f}x Classic's latency on this machine. "
              "The learned-evaluation path is therefore the clearest measured added cost and the next profiling target. "
              "This benchmark does not separate feature extraction from neural matrix operations, so it cannot identify which internal kernel dominates. "
              "See V2_OPTIMIZATION.md when comparing reference and optimized inference builds.", "",
              "Search trees differ with evaluator scores: nodes/sec and completed depth measure the combined evaluator/search behavior, "
              "not inference cost alone. Nodes and TT hits include work in the last interrupted iteration; depth counts only completed iterations. "
              "TT clearing, position loading, warm-up and reporting are excluded from measured search times. "
              "Actual elapsed time is used for throughput, including budget overshoot and early mate exits. "
              "Static latency is batch-average wall time including feature extraction, clipping, and loop overhead; it is not a per-call latency percentile. "
              "CPU scheduling, clocks and load affect results. These timings are specific to this machine/build.", ""]
    for budget, modes in report["summary"]["search"].items():
        hybrid, classic = modes["hybrid"], modes["classic"]
        lines.append(f"At {budget} ms, Hybrid completed {hybrid['average_depth_difference_vs_classic']:+.3f} plies versus Classic on average, "
                     f"with {hybrid['nodes_per_second']/classic['nodes_per_second']:.3f}x its search nodes/sec.")
    lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", type=Path, default=Path("build/Release/ChessAI_performance.exe"))
    parser.add_argument("--positions", type=Path, default=Path("benchmarks/performance-middlegames-v1.tsv"))
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--evaluations", type=int, default=200000)
    parser.add_argument("--warmup", type=int, default=10000)
    parser.add_argument("--budgets", default="100,250,1000")
    parser.add_argument("--output", type=Path, default=Path("benchmarks/performance_results.json"))
    args = parser.parse_args()
    if min(args.repetitions, args.evaluations, args.warmup) < 1:
        parser.error("Counts must be positive")
    if args.output.exists() or args.output.with_suffix(".md").exists():
        parser.error("Output exists; select a new output path to preserve prior measurements")
    machine = {"platform": platform.platform(), "machine": platform.machine(), "cpu": platform.processor(),
               "logical_cpus": os.cpu_count(), "python": platform.python_version()}
    if os.name == "nt":
        try:
            cpu = subprocess.check_output(["powershell", "-NoProfile", "-Command",
                "Get-CimInstance Win32_Processor | Select-Object Name,NumberOfCores,NumberOfLogicalProcessors | ConvertTo-Json -Compress"], text=True, timeout=15)
            machine["cpu_details"] = json.loads(cpu)
            machine["cpu"] = machine["cpu_details"]["Name"].strip()
        except (subprocess.SubprocessError, ValueError, KeyError, TypeError):
            pass
    started = datetime.now(timezone.utc).isoformat()
    command = [str(args.engine.resolve()), "--positions", str(args.positions.resolve()), "--repetitions", str(args.repetitions),
               "--evaluations", str(args.evaluations), "--warmup", str(args.warmup), "--budgets", args.budgets]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, text=True)
    try:
        stdout, _ = process.communicate()
        if process.returncode:
            raise RuntimeError(f"Native benchmark failed with code {process.returncode}; no report saved")
    except BaseException:
        process.kill(); process.wait()
        raise
    rows = [json.loads(line) for line in stdout.splitlines()]
    if rows[-1]["type"] != "complete":
        raise RuntimeError("Incomplete benchmark; no report saved")
    build_flags = {}
    cache = args.engine.parent.parent / "CMakeCache.txt"
    if cache.exists():
        for line in cache.read_text(encoding="utf-8").splitlines():
            if line.startswith(("CMAKE_CXX_FLAGS:", "CMAKE_CXX_FLAGS_RELEASE:", "CMAKE_GENERATOR:",
                                "CHESSAI_V2_OPTIMIZATION:", "CHESSAI_V2_ENABLE_AVX2:")):
                key, value = line.split("=", 1); build_flags[key] = value
    report = {"format_version": 1, "purpose": "performance-only, not strength", "started_utc": started,
              "finished_utc": datetime.now(timezone.utc).isoformat(), "machine": machine,
              "native_metadata": rows[0], "build_flags": build_flags,
              "engine_sha256": hashlib.sha256(args.engine.read_bytes()).hexdigest(),
              "manifest_sha256": hashlib.sha256(args.positions.read_bytes()).hexdigest(),
              "manifest_path": str(args.positions), "command": command,
              "time_budgets_ms": sorted({r["budget_ms"] for r in rows if r["type"] == "search"}),
              "positions": [r for r in rows if r["type"] == "position"],
              "summary": summarize(rows), "raw_measurements": [r for r in rows if r["type"] in ("static", "search")]}
    write_atomic(args.output, json.dumps(report, indent=2, allow_nan=False)+"\n")
    write_atomic(args.output.with_suffix(".md"), markdown(report))
    print(f"Wrote {args.output} and {args.output.with_suffix('.md')}")


if __name__ == "__main__":
    main()
