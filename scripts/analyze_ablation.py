#!/usr/bin/env python3
"""Summarise paired ablation runs without importing the model stack."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from statistics import mean
from typing import Any

METRICS = ("accuracy_final", "label_match_rate_of_covered", "coverage_final", "other_rate_final",
           "novel_absorbed", "births_beyond_seeds", "other_bucket_final", "low_confidence_final",
           "llm_calls", "re_route_count", "latency_p50", "rejected_proposals_duplicate",
           "dup_pair_count", "dup_pair_count_strict", "fragmentation_max", "n_junk")
HEADLINES = ("accuracy_final", "dup_pair_count", "fragmentation_max", "births_beyond_seeds",
             "novel_absorbed", "coverage_final", "other_rate_final", "low_confidence_share", "llm_calls")
# Add pairs here (left, right, label); the first side minus the second is reported.
COMPARISONS: tuple[tuple[str, str, str], ...] = (
    ("cold-as-today", "cold-blind", "cold as-today vs blind"),
    ("cold-hardened", "cold-blind", "cold hardened vs blind"),
    ("cold-system-placement", "cold-blind", "cold system-placement vs blind"),
    ("seeded-as-today", "seeded-blind", "seeded as-today vs blind"),
    ("seeded-hardened", "seeded-blind", "seeded hardened vs blind"),
    ("seeded-system-placement", "seeded-blind", "seeded system-placement vs blind"),
    ("seeded-blind", "cold-blind", "seeded vs cold blind"),
    ("seeded-as-today", "cold-as-today", "seeded vs cold as-today"),
    ("seeded-hardened", "cold-hardened", "seeded vs cold hardened"),
    ("seeded-system-placement", "cold-system-placement", "seeded vs cold system-placement"),
    ("cold-as-today", "anchor-cold-as-today", "none vs full cold as-today"),
    ("seeded-hardened", "anchor-seeded-hardened", "none vs full seeded hardened"),
    ("dedup-seeded-hardened", "seeded-hardened", "dedup seeded hardened vs base"),
    ("dedup-cold-hardened", "cold-hardened", "dedup cold hardened vs base"),
)

_FILE_RE = re.compile(r"^(?P<cell>.+)-fshot-(?P<fshot>[^-]+)-p(?P<seed>\d+)(?:-dedup-(?P<dedup>.+?))?(?:-r(?P<repeat>\d+))?\.json$")


def parse_filename(path: str | Path) -> dict[str, Any] | None:
    """Parse run_ablation's filename, including optional dedup and repeat suffixes."""
    m = _FILE_RE.match(Path(path).name)
    if not m:
        return None
    return {"cell": m["cell"], "few_shot": m["fshot"], "permutation_seed": int(m["seed"]),
            "dedup_tag": m["dedup"], "repeat": int(m["repeat"] or 0), "path": str(path)}


# Descriptive alias for callers embedding this analysis module.
parse_run_filename = parse_filename


def _value(run: dict[str, Any], metric: str) -> Any:
    metrics = run.get("metrics") if isinstance(run.get("metrics"), dict) else {}
    if metric == "latency_p50":
        latency = run.get("latency") if isinstance(run.get("latency"), dict) else {}
        return latency.get("p50", latency.get("p50_ms"))
    if metric == "llm_calls":
        return (run.get("meta") or {}).get("llm_calls", run.get("llm_calls"))
    if metric == "rejected_proposals_duplicate":
        return (metrics.get("rejected_proposals") or {}).get("duplicate")
    return metrics.get(metric)


def _mean(values: list[Any]) -> float | None:
    nums = [float(x) for x in values if isinstance(x, (int, float)) and not isinstance(x, bool)]
    return mean(nums) if nums else None


def _stat(values: list[Any]) -> dict[str, float | None]:
    nums = [float(x) for x in values if isinstance(x, (int, float)) and not isinstance(x, bool)]
    return {"mean": round(mean(nums), 10) if nums else None, "min": round(min(nums), 10) if nums else None,
            "max": round(max(nums), 10) if nums else None,
            "range": round(max(nums) - min(nums), 10) if nums else None}


def gate_decomposition(runs: list[dict[str, Any]]) -> dict[str, Any]:
    low = _mean([_value(r, "low_confidence_final") for r in runs])
    bucket = _mean([_value(r, "other_bucket_final") for r in runs])
    total = (low or 0) + (bucket or 0)
    return {"low_confidence_final": low, "other_bucket_final": bucket,
            "low_confidence_share": low / total if total else None,
            "other_bucket_share": bucket / total if total else None,
            "other_rate_final": _mean([_value(r, "other_rate_final") for r in runs])}


def aggregate_runs(runs: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate by seed first, so repeats cannot overweight a permutation seed."""
    by_seed: dict[Any, list[dict[str, Any]]] = {}
    for r in runs:
        by_seed.setdefault(r.get("_parsed", {}).get("permutation_seed"), []).append(r)
    seed_values: dict[str, list[float]] = {}
    for metric in METRICS:
        vals = []
        for group in by_seed.values():
            value = _mean([_value(r, metric) for r in group])
            if value is not None:
                vals.append(value)
        seed_values[metric] = vals
    aggregate = {metric: _stat(values) for metric, values in seed_values.items()}
    aggregate["n_seeds"] = len(by_seed)
    aggregate["n_runs"] = len(runs)
    aggregate["gate_decomposition"] = gate_decomposition(runs)
    low, bucket = aggregate["gate_decomposition"]["low_confidence_share"], aggregate["gate_decomposition"]["other_bucket_share"]
    aggregate["low_confidence_share"] = {"mean": low, "min": low, "max": low, "range": 0.0} if low is not None else _stat([])
    aggregate["other_bucket_share"] = {"mean": bucket, "min": bucket, "max": bucket, "range": 0.0} if bucket is not None else _stat([])
    return aggregate


def paired_deltas(left: list[dict[str, Any]], right: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    def indexed(rows: list[dict[str, Any]]) -> dict[Any, dict[str, Any]]:
        return {r.get("_parsed", {}).get("permutation_seed"): r for r in rows}
    a, b = indexed(left), indexed(right)
    result = {}
    for metric in METRICS + ("low_confidence_share",):
        deltas = []
        for seed in sorted(set(a) & set(b), key=str):
            if metric == "low_confidence_share":
                av = gate_decomposition([a[seed]])["low_confidence_share"]
                bv = gate_decomposition([b[seed]])["low_confidence_share"]
            else:
                av, bv = _value(a[seed], metric), _value(b[seed], metric)
            if isinstance(av, (int, float)) and isinstance(bv, (int, float)):
                deltas.append(av - bv)
        result[metric] = _stat(deltas)
    return result


def noise_floor(runs: list[dict[str, Any]]) -> dict[str, Any] | None:
    groups: dict[tuple[Any, Any], dict[int, dict[str, Any]]] = {}
    for r in runs:
        p = r.get("_parsed", {})
        groups.setdefault((p.get("cell"), p.get("permutation_seed")), {})[p.get("repeat", 0)] = r
    diffs: dict[str, list[float]] = {m: [] for m in METRICS}
    for pair in groups.values():
        if 1 not in pair or 2 not in pair:
            continue
        for metric in METRICS:
            x, y = _value(pair[1], metric), _value(pair[2], metric)
            if isinstance(x, (int, float)) and isinstance(y, (int, float)):
                diffs[metric].append(abs(x - y))
    if not any(diffs.values()):
        return None
    return {metric: _stat(values) for metric, values in diffs.items()}


def render_markdown(cells: dict[str, Any], comparisons: dict[str, Any], noise: Any) -> str:
    def fmt(v: Any) -> str:
        if not isinstance(v, dict) or v.get("mean") is None: return "—"
        return f"{v['mean']:.3g}±{(v.get('range') or 0):.3g}"
    lines = ["| Cell | " + " | ".join(HEADLINES) + " |", "|---|" + "---:|" * len(HEADLINES)]
    for name, cell in cells.items():
        vals = [cell.get("low_confidence_share") if key == "low_confidence_share" else cell.get(key) for key in HEADLINES]
        lines.append("| " + name + " | " + " | ".join(fmt(v) for v in vals) + " |")
    lines += ["", "| Paired comparison (left − right) | Metric | Mean±range |", "|---|---|---:|"]
    for label, data in comparisons.items():
        for metric, value in data.items(): lines.append(f"| {label} | {metric} | {fmt(value)} |")
    lines += ["", "| Noise floor | Metric | Absolute mean±range |", "|---|---|---:|"]
    if noise is None: lines.append("| repeats unavailable | — | — |")
    else:
        for metric, value in noise.items(): lines.append(f"| repeats | {metric} | {fmt(value)} |")
    return "\n".join(lines) + "\n"


def _load(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def _path_keys(path: str | Path) -> tuple[str, ...]:
    """Return stable aliases used by judge files from different invocations."""
    raw = str(path)
    resolved = str(Path(path).resolve())
    name = Path(path).name
    return tuple(dict.fromkeys((raw, resolved, name)))


def _judge_summary(judge: dict[str, Any], path: str | Path) -> dict[str, Any]:
    """Find a judge result whether it was saved with relative or absolute paths."""
    for key in _path_keys(path):
        value = judge.get(key)
        if isinstance(value, dict):
            summary = value.get("summary")
            return summary if isinstance(summary, dict) else {}
    target = str(Path(path).resolve())
    for key, value in judge.items():
        if key == "run_config" or not isinstance(value, dict):
            continue
        if str(Path(key).resolve()) == target:
            summary = value.get("summary")
            return summary if isinstance(summary, dict) else {}
    return {}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ablation-dir", required=True, type=Path)
    parser.add_argument("--baselines", nargs="*", type=Path, default=[])
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--table-out", type=Path)
    judge_group = parser.add_mutually_exclusive_group()
    judge_group.add_argument("--judge", action="store_true")
    judge_group.add_argument("--skip-judge", action="store_true", help="explicitly disable registry judging")
    args = parser.parse_args(argv)
    if not args.ablation_dir.is_dir():
        print(f"ablation directory does not exist: {args.ablation_dir}", file=sys.stderr)
        return 1
    groups: dict[tuple[str, str | None], list[dict[str, Any]]] = {}
    paths = sorted(args.ablation_dir.glob("*.json"))
    for path in paths:
        parsed = parse_filename(path)
        if not parsed:
            print(f"skipping unparseable ablation file: {path}", file=sys.stderr); continue
        data = _load(path)
        if data is None: print(f"skipping invalid JSON: {path}", file=sys.stderr); continue
        data["_parsed"] = parsed
        groups.setdefault((parsed["cell"], parsed["dedup_tag"]), []).append(data)
    baseline_data = [(str(p), _load(p)) for p in args.baselines if _load(p) is not None]
    judge: dict[str, Any] = {}
    judge_out = args.ablation_dir / "judge.json"
    loaded_judge = _load(judge_out)
    if loaded_judge is not None:
        judge = loaded_judge
    if args.judge:
        judge_paths = [str(p) for p in paths] + [p for p, _ in baseline_data]
        if judge_paths:
            subprocess.run(["uv", "run", "python", "scripts/judge_registry.py", *judge_paths, "--out", str(judge_out)], check=True)
            loaded = _load(judge_out)
            judge = loaded or {}
    cells: dict[str, Any] = {}
    cell_runs: dict[str, list[dict[str, Any]]] = {}
    consistency_issues: list[dict[str, Any]] = []
    for (cell, dedup), runs in groups.items():
        name = cell + (f" [dedup:{dedup}]" if dedup else "")
        agg = aggregate_runs(runs)
        for metric in ("dup_pair_count", "dup_pair_count_strict", "fragmentation_max", "n_junk"):
            vals = []
            for r in runs:
                summary = _judge_summary(judge, r["_parsed"]["path"])
                vals.append(summary.get(metric))
            agg[metric] = _stat(vals)
        agg["low_confidence_share"] = {"mean": agg["gate_decomposition"]["low_confidence_share"], "range": None, "min": None, "max": None}
        cells[name] = agg; cell_runs[name] = runs
        expected_proposer = cell.removeprefix("anchor-").removeprefix("stress-").removeprefix("dedup-").split("-", 1)[-1]
        for run in runs:
            config = run.get("run_config") or {}
            expected = {"proposer_mode": expected_proposer, "few_shot": run["_parsed"].get("few_shot")}
            actual = {key: config.get(key) for key in expected}
            divergent = {key: {"expected": value, "actual": actual[key]} for key, value in expected.items()
                         if actual[key] is not None and actual[key] != value}
            if divergent: consistency_issues.append({"path": run["_parsed"]["path"], "cell": cell, "differences": divergent})
    comparisons: dict[str, Any] = {}
    for left, right, label in COMPARISONS:
        lkey = next((k for k in cell_runs if k == left or k.startswith(left + " [")), None)
        rkey = next((k for k in cell_runs if k == right or k.startswith(right + " [")), None)
        if lkey and rkey: comparisons[label] = paired_deltas(cell_runs[lkey], cell_runs[rkey])
    baselines = []
    for path, data in baseline_data:
        row = {"path": path, "accuracy_final": _value(data, "accuracy_final"), "label_match_rate_of_covered": _value(data, "label_match_rate_of_covered"),
               "coverage_final": _value(data, "coverage_final"), "other_rate_final": _value(data, "other_rate_final"), "llm_calls": _value(data, "llm_calls")}
        row["judge"] = _judge_summary(judge, path)
        baselines.append(row)
    output = {"cells": cells, "paired_deltas": comparisons, "noise_floor": noise_floor([r for runs in cell_runs.values() for r in runs]),
              "baselines": baselines, "run_config_consistency": {"ok": not consistency_issues, "issues": consistency_issues}}
    text = render_markdown(cells, comparisons, output["noise_floor"])
    args.out.parent.mkdir(parents=True, exist_ok=True); args.out.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    if args.table_out: args.table_out.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__": raise SystemExit(main())
