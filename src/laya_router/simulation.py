"""Closed-loop simulation: prompts stream through the router; 'other' events
accumulate and periodically trigger category-creation, then are re-routed
once the new categories exist. Everything is logged for the visualizer."""

from __future__ import annotations

import json
import time

from .router import SelfEvolvingRouter

LEARN_BATCH = 10


def run_simulation(
    router: SelfEvolvingRouter,
    dataset_path: str,
    learn_interval: int = LEARN_BATCH,
) -> dict:
    """Streams the dataset once. Every `learn_interval` 'other' events trigger
    one LLM call; newly created categories immediately re-classify the
    pending 'other' prompts against the grown registry."""
    with open(dataset_path, encoding="utf-8") as f:
        prompts = [json.loads(line) for line in f if line.strip()]

    events: list[dict] = []
    creations: list[dict] = []
    pending_other: list[dict] = []  # events waiting for new categories

    t_start = time.perf_counter()
    for i, p in enumerate(prompts):
        ev = router.route(p["id"], p["text"], step=i)
        ev["ground_truth"] = p["ground_truth"]
        ev["correct"] = ev["route"] == p["ground_truth"]
        events.append(ev)
        if ev["route"] == OTHER:
            pending_other.append(ev)
            if len(pending_other) >= learn_interval:
                creations.extend(router.learn_from_others(pending_other, step=i))
                pending_other = _retry_pending(router, pending_other, i, events)

    # Final drain of leftovers
    leftovers = list(pending_other)
    while leftovers and not router.registry.is_full():
        before = router.registry.names()
        creations.extend(router.learn_from_others(leftovers, step=len(prompts)))
        survivors = _retry_pending(router, leftovers, len(prompts), events)
        if router.registry.names() == before:  # LLM produced nothing new: stop
            break
        leftovers = survivors

    wall = time.perf_counter() - t_start
    latencies = [e["latency_ms"] for e in events]
    return {
        "meta": {
            "backend": router.backend,
            "model": router.stats()["backend"],
            "threshold": router.threshold,
            "n_prompts": len(prompts),
            "wall_seconds": round(wall, 2),
            "llm_calls": router.llm_calls,
        },
        "events": events,
        "category_creations": creations,
        "registry_final": router.stats(),
        "growth_history": router.registry.growth_history(),
        "metrics": _summary_metrics(events, creations),
        "latency": {
            "p50": _pct(latencies, 50),
            "p95": _pct(latencies, 95),
            "mean": round(sum(latencies) / len(latencies), 2),
        },
    }


def _retry_pending(
    router: SelfEvolvingRouter, pending: list[dict], step: int, events: list[dict]
) -> list[dict]:
    """Re-classify pending 'other' prompts; keep survivors as still-other."""
    survivors = []
    for ev in pending:
        rev = router.route(ev["id"], ev["text"], step=step)
        rev["ground_truth"] = ev["ground_truth"]
        rev["correct"] = rev["route"] == rev["ground_truth"]
        rev["rerouted"] = True
        events.append(rev)
        if rev["route"] == OTHER:
            survivors.append(rev)
    return survivors


def _pct(xs: list[float], p: int) -> float:
    if not xs:
        return 0.0
    s = sorted(xs)
    k = max(0, min(len(s) - 1, int(len(s) * p / 100)))
    return round(s[k], 2)


def _summary_metrics(events: list[dict], creations: list[dict]) -> dict:
    final = {}
    for e in events:  # last routing decision wins (re-routes overwrite)
        final[e["id"]] = e
    final_events = list(final.values())
    n = len(final_events)
    correct = sum(1 for e in final_events if e.get("correct"))
    routed_other = sum(1 for e in final_events if e["route"] == OTHER)
    handled_ground_truth = [
        e for e in final_events if e["ground_truth"].startswith("novel")
    ]
    novel_other = [e for e in handled_ground_truth if e["route"] == OTHER]
    return {
        "accuracy_final": round(correct / n, 4) if n else 0,
        "other_rate_final": round(routed_other / n, 4) if n else 0,
        "novel_prompts": len(handled_ground_truth),
        "novel_final_other": len(novel_other),
        "modified_records": len(events) - len(final_events),  # re-route count
    }
