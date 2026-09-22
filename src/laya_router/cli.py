"""CLI: run the simulation or route a single typed prompt live."""

from __future__ import annotations

import argparse
import json
import os
import sys

from .llm import load_providers
from .router import SelfEvolvingRouter
from .simulation import run_simulation

PROPOSER_MODES = ["blind", "as-today", "hardened", "system-placement"]
FEWSHOT_CHOICES = ["none", "three", "full"]
DEDUP_CHOICES = ["none", "token-jaccard-025"]


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Self-evolving Laya router")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sim = sub.add_parser("simulate", help="run the closed-loop simulation")
    sim.add_argument("--dataset", default="data/dataset.jsonl")
    sim.add_argument("--out", default="results/results.json")
    sim.add_argument("--backend", default="mlx", choices=["mlx", "coreml"])
    sim.add_argument("--model", default=None, help="laya checkpoint id or dir")
    sim.add_argument("--threshold", type=float, default=0.5)
    sim.add_argument("--seed", type=int, default=None, help="permutation seed (default: file order)")
    sim.add_argument("--seed-file", default=None, help="JSON list of {name, description} seed categories")
    sim.add_argument("--proposer", default="as-today", choices=PROPOSER_MODES)
    sim.add_argument("--few-shot", default=None, choices=FEWSHOT_CHOICES,
                     help="few-shot examples (default: env LAYASYS_FEWSHOT, else full)")
    sim.add_argument("--dedup", default="none", choices=DEDUP_CHOICES)

    live = sub.add_parser("live", help="route a prompt and watch categories grow")
    live.add_argument("--backend", default="mlx", choices=["mlx", "coreml"])
    live.add_argument("--model", default=None)
    live.add_argument("--threshold", type=float, default=0.5)
    live.add_argument("--seed-file", default=None, help="JSON list of {name, description} seed categories")
    live.add_argument("--proposer", default="as-today", choices=PROPOSER_MODES)
    live.add_argument("--few-shot", default=None, choices=FEWSHOT_CHOICES,
                      help="few-shot examples (default: env LAYASYS_FEWSHOT, else full)")
    live.add_argument("--dedup", default="none", choices=DEDUP_CHOICES)

    return ap


def _resolve_few_shot(arg_few_shot: str | None) -> str:
    """CLI flag wins; otherwise fall back to env LAYASYS_FEWSHOT, then "full"."""
    if arg_few_shot is not None:
        return arg_few_shot
    return os.getenv("LAYASYS_FEWSHOT", "full").strip().lower()


def _resolve_dedup(value: str | None) -> str | None:
    return "token_jaccard_025" if value == "token-jaccard-025" else None


def _load_seed_categories(path: str | None) -> list[dict] | None:
    """Load a seed-file JSON list of {"name", "description"} dicts."""
    if path is None:
        return None
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"seed file {path} must contain a JSON list")
    for item in data:
        if not isinstance(item, dict) or "name" not in item or "description" not in item:
            raise ValueError(f"seed file {path} entries need 'name' and 'description'")
    return data


def main() -> None:
    args = build_parser().parse_args()

    if args.backend == "mlx":
        model = args.model or "aac6fef/laya-mlx"
    else:
        model = args.model or "aac6fef/laya-coreml"

    few_shot = _resolve_few_shot(args.few_shot)
    extra_dedup = _resolve_dedup(args.dedup)
    initial_categories = _load_seed_categories(args.seed_file)

    router = SelfEvolvingRouter(
        proposer=load_providers(),
        confidence_threshold=args.threshold,
        laya_model=model,
        backend=args.backend,
        proposer_mode=args.proposer,
        few_shot=few_shot,
        initial_categories=initial_categories,
        extra_dedup=extra_dedup,
    )
    print(f"Router ready | backend={args.backend} model={model} dedup={args.dedup}", file=sys.stderr)

    if args.cmd == "simulate":
        print(
            f"run config | dataset={args.dataset} backend={args.backend} model={model} "
            f"threshold={args.threshold} proposer={args.proposer} few_shot={few_shot} "
            f"seed={args.seed} seed_file={args.seed_file} "
            f"initial_categories={len(initial_categories or [])} dedup={args.dedup}",
            file=sys.stderr,
        )
        results = run_simulation(
            router,
            args.dataset,
            seed=args.seed,
            seed_set_name=args.seed_file,
        )
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        print(json.dumps(results["metrics"], indent=2))
        print(json.dumps(results["latency"], indent=2))
        print(f"categories: {router.registry.names()}")
        print(f"saved -> {args.out}")
    else:
        pending = []
        while True:
            try:
                text = input("\nprompt> ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not text:
                continue
            step = 0  # live mode: steps purely informational
            ev = router.route("live", text, step)
            print(json.dumps(ev, indent=2, ensure_ascii=False))
            if ev["route"] == "other":
                pending.append(ev)
                created = router.learn_from_others(pending, step)
                pending = []
                for c in created:
                    print(f"  + new category: {c['name']} — {c['description']}")
                if not created:
                    print("  (no new category proposed by the LLM)")


if __name__ == "__main__":
    main()
