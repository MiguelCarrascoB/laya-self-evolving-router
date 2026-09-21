"""CLI: run the simulation or route a single typed prompt live."""

from __future__ import annotations

import argparse
import json
import sys

from .llm import load_providers
from .router import SelfEvolvingRouter
from .simulation import run_simulation


def main() -> None:
    ap = argparse.ArgumentParser(description="Self-evolving Laya router")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sim = sub.add_parser("simulate", help="run the closed-loop simulation")
    sim.add_argument("--dataset", default="data/dataset.jsonl")
    sim.add_argument("--out", default="results/results.json")
    sim.add_argument("--backend", default="mlx", choices=["mlx", "coreml"])
    sim.add_argument("--model", default=None, help="laya checkpoint id or dir")
    sim.add_argument("--threshold", type=float, default=0.5)

    live = sub.add_parser("live", help="route a prompt and watch categories grow")
    live.add_argument("--backend", default="mlx", choices=["mlx", "coreml"])
    live.add_argument("--model", default=None)
    live.add_argument("--threshold", type=float, default=0.5)

    args = ap.parse_args()

    if args.backend == "mlx":
        model = args.model or "aac6fef/laya-mlx"
    else:
        model = args.model or "aac6fef/laya-coreml"

    router = SelfEvolvingRouter(
        proposer=load_providers(),
        confidence_threshold=args.threshold,
        laya_model=model,
        backend=args.backend,
    )
    print(f"Router ready | backend={args.backend} model={model}", file=sys.stderr)

    if args.cmd == "simulate":
        results = run_simulation(router, args.dataset)
        import os
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
