"""Measure Laya routing quality over fixed registries, without LLM calls.

The module deliberately imports only the standard library.  Laya is imported
inside :func:`run`, so the pure registry and metric helpers remain CI-safe.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable

OTHER = "other"
CANONICAL = [
    ("coding_help", "Debugging, refactoring, or explaining programming problems."),
    ("translation", "Converting text between languages or adjusting its register."),
    ("data_analysis", "Summarizing, comparing, or finding patterns in data."),
    ("scheduling", "Planning, reminding, or distributing tasks across time."),
    ("shopping", "Choosing, comparing, or buying products and gifts."),
    ("math_homework", "Solving or explaining math problems and exercises."),
    ("cooking_recipes", "Recipes, ingredients, and meal preparation."),
    ("fitness_health", "Exercise, workouts, and physical-health questions."),
    ("travel_planning", "Planning trips, destinations, and itineraries."),
    ("writing_editing", "Improving, rewriting, or polishing written text."),
]
NOVEL = {
    "novel_astronomy": "Learning about stars, planets, and astronomical phenomena.",
    "novel_beekeeping": "Keeping bees, managing hives, and producing honey.",
    "novel_board_games": "Learning, comparing, or playing board games.",
    "novel_car_maintenance": "Maintaining, repairing, and troubleshooting cars.",
    "novel_esports_betting": "Betting on esports matches, teams, and tournaments.",
    "novel_genealogy_research": "Researching family history, ancestry, and genealogical records.",
    "novel_home_plants": "Growing, caring for, and troubleshooting houseplants.",
    "novel_music_theory": "Understanding music theory, harmony, and composition.",
    "novel_watch_collecting": "Collecting, evaluating, and caring for watches.",
    "novel_wine_tasting": "Tasting, comparing, and understanding wines.",
}

# The historical result file stores names (not descriptions).  These concise
# descriptions preserve the file's birth order while making its registry usable.
DISCOVERED_DESCRIPTIONS = {
    "coding_help": "Debugging and explaining programming problems.", "math_homework": "Solving math problems and exercises.",
    "scheduling": "Planning and distributing tasks across time.", "fitness_health": "Exercise and physical-health questions.",
    "travel_planning": "Planning trips and itineraries.", "shopping": "Choosing and comparing products.",
    "cooking_recipes": "Recipes, ingredients, and meal preparation.", "game_rules": "Understanding rules for games.",
    "beekeeping": "Keeping bees and managing hives.", "writing_editing": "Improving and rewriting written text.",
    "data_analysis": "Summarizing and finding patterns in data.", "translation": "Converting text between languages.",
    "genealogy": "Researching family history and ancestry.", "watch_care": "Caring for and maintaining watches.",
    "data_wrangling": "Cleaning and restructuring datasets.", "astronomy": "Learning about stars and planets.",
    "plant_care": "Growing and caring for plants.", "vehicle_maintenance": "Maintaining and repairing vehicles.",
    "food_safety": "Handling and storing food safely.", "sports_betting": "Betting on sports matches and teams.",
    "travel_logistics": "Managing transport and travel arrangements.", "language_interpretation": "Interpreting meaning across languages.",
    "music_composition": "Composing and arranging music.", "home_improvement": "Repairing and improving homes.",
    "language_learning": "Learning and practicing a language.", "wine_tasting": "Tasting and comparing wines.",
    "game_design": "Designing games and game mechanics.", "calendar_dates": "Understanding calendars and dates.",
    "watch_mechanics": "Understanding mechanical watch movements.", "statistical_methods": "Applying statistical methods to data.",
}


def bucket(n_options: int) -> str:
    if n_options == 2:
        return "2"
    if n_options <= 5:
        return "3-5"
    if n_options <= 10:
        return "6-10"
    return "11+"


def select_registry(family: str, size: int, discovered: list[dict[str, str]] | None = None) -> list[dict[str, str]]:
    items = ([{"name": n, "description": d} for n, d in CANONICAL]
             + [{"name": n, "description": NOVEL[n]} for n in sorted(NOVEL)]) if family == "perfect" else (discovered or [])
    return items[:size]


def top2_margin(probabilities: dict[str, float]) -> float:
    values = sorted(probabilities.values(), reverse=True)
    return values[0] - values[1] if len(values) >= 2 else 0.0


def compute_metrics(rows: list[dict[str, Any]], n_options: int) -> dict[str, Any]:
    n = len(rows)
    denom = max(n, 1)
    exact = sum(r["choice"] == r["ground_truth"] for r in rows)
    stripped = sum(r["choice"] == r["ground_truth"].removeprefix("novel_") for r in rows)
    non_other = [r for r in rows if r["choice"] != OTHER]
    def rate(predicate: Any) -> float:
        return sum(predicate(r) for r in non_other) / max(len(non_other), 1)
    metrics: dict[str, Any] = {
        "accuracy_exact": exact / denom, "accuracy_stripped": stripped / denom,
        "other_rate": sum(r["choice"] == OTHER for r in rows) / denom,
        "gate_entropy0.5": rate(lambda r: r["confidence"] < 0.5),
        "gate_topprob0.5": rate(lambda r: r["top_prob"] < 0.5),
        "gate_topprob0.9": rate(lambda r: r["top_prob"] < 0.9),
        "mean_confidence": sum(r["confidence"] for r in rows) / denom,
        "min_confidence": min((r["confidence"] for r in rows), default=0.0),
        "mean_top_prob": sum(r["top_prob"] for r in rows) / denom,
        "mean_top2_margin": sum(r["top2_margin"] for r in rows) / denom,
        "mean_input_tokens": sum(r["input_tokens"] for r in rows) / denom,
    }
    metrics["buckets"] = {}
    b = bucket(n_options)
    metrics["buckets"][b] = {"accuracy_exact": metrics["accuracy_exact"], "other_rate": metrics["other_rate"], "n": n}
    return metrics


def assemble_config(family: str, k: int, policy: str, routes: list[dict[str, Any]]) -> dict[str, Any]:
    result = {"family": family, "k": k, "policy": policy, "n_options": k + 1}
    result.update(compute_metrics(routes, k + 1))
    result["routes"] = routes
    return result


def load_discovered(path: Path) -> list[dict[str, str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    raw = data["registry_final"]["categories"]
    # Historical results store registry categories as names only; recover the
    # real birth descriptions from category_creations (by name), falling back
    # to the hand-written map only when a name is missing there.
    created = {c["name"]: c.get("description", "") for c in data.get("category_creations", [])}
    out = []
    for item in raw:
        if isinstance(item, dict):
            out.append({"name": item["name"], "description": item.get("description", "")})
        else:
            out.append({"name": item, "description": created.get(item) or DISCOVERED_DESCRIPTIONS.get(item, "")})
    return out


def run(args: argparse.Namespace) -> dict[str, Any]:
    # Lazy import is important: helper tests run on Linux without laya-mlx.
    # The laya packages install as backend-specific top-level modules.
    if args.backend == "coreml":
        import laya_coreml as laya  # type: ignore
        agent = laya.load(args.model)
    else:
        import laya_mlx as laya  # type: ignore
        agent = laya.load(args.model, dtype="float16")
    prompts = [json.loads(line) for line in Path(args.dataset).read_text(encoding="utf-8").splitlines() if line.strip()]
    if args.limit is not None:
        prompts = prompts[:args.limit]
    discovered = load_discovered(Path(args.discovered))
    families = {"perfect": select_registry("perfect", 20), "discovered": discovered}
    configs = []
    for family, all_categories in families.items():
        for k in args.sizes:
            if k > len(all_categories):
                print(f"skip {family} k={k}: only {len(all_categories)} categories", file=sys.stderr)
                continue
            for policy in ("full", "name-only"):
                categories = select_registry(family, k, all_categories)
                criteria = {c["name"]: c["description"] if policy == "full" else "" for c in categories}
                criteria[OTHER] = "none of the other options fit this request"
                routes = []
                for i, prompt in enumerate(prompts, 1):
                    question = {"intent": {"type": "choice", "instructions": "Which category best matches this user request's intent?", "criteria": criteria}}
                    prediction = agent.predict(prompt["text"], question)
                    answer = prediction["answers"]["intent"]
                    probs = answer.get("probabilities", {})
                    choice = answer["choice"]
                    routes.append({"id": prompt["id"], "ground_truth": prompt["ground_truth"], "choice": choice,
                                   "confidence": float(answer.get("confidence", 0.0)), "top_prob": float(probs.get(choice, 0.0)),
                                   "top2_margin": top2_margin(probs), "input_tokens": prediction.get("usage", {}).get("input_tokens", 0)})
                    if i % 50 == 0:
                        print(f"{family} k={k} {policy}: {i}/{len(prompts)}", file=sys.stderr)
                configs.append(assemble_config(family, k, policy, routes))
    output = {"run_config": {"dataset": args.dataset, "model": args.model, "backend": args.backend, "limit": args.limit}, "configs": configs}
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print("| family | k | policy | exact | other | entropy<.5 | tokens |\n|---|---:|---|---:|---:|---:|---:|")
    for c in configs:
        print(f"| {c['family']} | {c['k']} | {c['policy']} | {c['accuracy_exact']:.3f} | {c['other_rate']:.3f} | {c['gate_entropy0.5']:.3f} | {c['mean_input_tokens']:.1f} |")
    return output


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dataset", default="data/dataset.jsonl", help="JSONL prompts with id/text/ground_truth (default: %(default)s)")
    p.add_argument("--model", default="aac6fef/laya-mlx", help="Laya model id (default: %(default)s)")
    p.add_argument("--backend", default="mlx", help="Laya backend: mlx or coreml (default: %(default)s)")
    p.add_argument("--out", default="results/probe/probe_results.json", help="output JSON (default: %(default)s)")
    p.add_argument("--sizes", default="4,9,10,15,30", help="comma-separated registry sizes k (default: %(default)s)")
    p.add_argument("--discovered", default="results/results-v3-full.json", help="results JSON whose final registry is the 'discovered' family")
    p.add_argument("--limit", type=int, help="only probe the first N prompts")
    args = p.parse_args()
    try:
        args.sizes = [int(x) for x in args.sizes.split(",") if x.strip()]
    except ValueError:
        p.error(f"--sizes must be comma-separated integers, got {args.sizes!r}")
    run(args)


if __name__ == "__main__":
    main()
