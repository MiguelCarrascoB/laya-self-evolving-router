"""Semantic accuracy from judge mappings × actual routes.

Reads results/ablation/judge.json (category → ground-truth intent mappings) and
every run's final routes, and scores each run semantically: a route counts as
correct when its category's JUDGED intent equals the prompt's ground truth.

Usage: uv run python scripts/semantic_accuracy.py [--judge results/ablation/judge.json]
"""
from __future__ import annotations

import argparse
import glob
import json
import re
from collections import defaultdict

SKIP_SUFFIXES = ("ledger.json", "summary.json", "analysis.json", "judge.json")


def load_mappings(judge_path: str) -> dict[str, dict[str, str]]:
    judge = json.load(open(judge_path))
    out = {}
    for key, val in judge.items():
        if key == "run_config" or not isinstance(val, dict):
            continue
        out[key] = {
            e["name"]: e["mapped_to"]
            for e in val.get("mapping", [])
            if isinstance(e, dict) and "name" in e
        }
    return out


def score_run(data: dict, mapping: dict[str, str]) -> tuple[float, float, float, int]:
    final = {}
    for ev in data["events"]:
        final[ev["id"]] = ev  # last decision wins
    n = sem_correct = sem_cov = 0
    for ev in final.values():
        n += 1
        route, gt = ev["route"], ev["ground_truth"]
        if route == "other":
            continue
        sem_cov += 1
        mapped = mapping.get(route, route)
        if mapped == gt or mapped == gt.removeprefix("novel_"):
            sem_correct += 1
    return (sem_correct / max(n, 1), sem_correct / max(sem_cov, 1), sem_cov / max(n, 1), n)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--judge", default="results/ablation/judge.json")
    parser.add_argument("--ablation-dir", default="results/ablation")
    args = parser.parse_args()
    mappings = load_mappings(args.judge)
    agg: dict[str, list[tuple[float, float, float]]] = defaultdict(list)
    for path in sorted(glob.glob(f"{args.ablation_dir}/*.json")):
        if path.endswith(SKIP_SUFFIXES):
            continue
        data = json.load(open(path))
        if not isinstance(data, dict) or "events" not in data:
            continue
        cell = re.sub(r"-fshot-.*", "", path.split("/")[-1])
        acc, match, cov, _ = score_run(data, mappings.get(path, {}))
        agg[cell].append((acc, match, cov))
    print("cell  semantic_acc±spread  semantic_label_match  semantic_coverage  (n)")
    for cell in sorted(agg):
        vals = agg[cell]
        k = len(vals)
        a = sum(v[0] for v in vals) / k
        lm = sum(v[1] for v in vals) / k
        c = sum(v[2] for v in vals) / k
        spread = max(v[0] for v in vals) - min(v[0] for v in vals)
        print(f"{cell}  {a:.3f}±{spread:.3f}  {lm:.3f}  {c:.3f}  (n={k})")


if __name__ == "__main__":
    main()
