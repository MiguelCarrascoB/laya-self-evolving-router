"""Closed-loop simulation: prompts stream through the router; 'other' events
accumulate and periodically trigger category-creation, then are re-routed
once the new categories exist. Everything is logged for the visualizer."""

from __future__ import annotations

import datetime
import hashlib
import json
import random
import subprocess
import time

from .metrics import compute_metrics
from .router import OTHER, SelfEvolvingRouter

LEARN_BATCH = 10
MAX_REROUTES = 2


def run_simulation(
    router: SelfEvolvingRouter,
    dataset_path: str,
    learn_interval: int = LEARN_BATCH,
    *,
    seed: int | None = None,
    seed_set_name: str | None = None,
) -> dict:
    """Streams the dataset once. Every `learn_interval` 'other' events trigger
    one LLM call; newly created categories immediately re-classify the
    pending 'other' prompts against the grown registry.

    ``seed=None`` streams the dataset in file order; ``seed=<int>`` applies a
    deterministic ``random.Random(seed).shuffle`` permutation first, so paired
    runs across registry/proposer cells compare the same prompt order.
    """
    prompts = _load_prompts(dataset_path, seed)

    events: list[dict] = []
    creations: list[dict] = []
    pending_other: list[dict] = []  # events waiting for new categories
    retry_guess: dict[str, int] = {}  # otherwise unbounded churn
    max_reroutes = MAX_REROUTES

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
                pending_other = _retry_pending(
                    router, pending_other, i, events, retry_guess, max_reroutes
                )

    # Final drain of leftovers
    leftovers = list(pending_other)
    while leftovers and not router.registry.is_full():
        before = router.registry.names()
        creations.extend(router.learn_from_others(leftovers, step=len(prompts)))
        survivors = _retry_pending(
            router, leftovers, len(prompts), events, retry_guess, max_reroutes
        )
        if router.registry.names() == before:  # LLM produced nothing new: stop
            break
        leftovers = survivors

    wall = time.perf_counter() - t_start
    latencies = [e["latency_ms"] for e in events]
    seeded = {j["ground_truth"] for j in prompts if not j["ground_truth"].startswith("novel")}

    registry_dicts = router.registry.as_dicts()
    registry_final = router.stats()
    registry_final["categories"] = registry_dicts

    return {
        "meta": {
            "backend": router.backend,
            "model": router.laya_model,
            "proposer_model": _proposer_model(router.proposer),
            "threshold": router.threshold,
            "n_prompts": len(prompts),
            "wall_seconds": round(wall, 2),
            "llm_calls": router.llm_calls,
        },
        "run_config": _build_run_config(router, dataset_path, seed, seed_set_name),
        "events": events,
        "category_creations": creations,
        "registry_final": registry_final,
        "seed_rejections": router.registry.seed_rejections,
        "growth_history": router.registry.growth_history(),
        "metrics": compute_metrics(events, registry_dicts, seeded, router.registry.rejections),
        "latency": {
            "p50": _pct(latencies, 50),
            "p95": _pct(latencies, 95),
            "mean": round(sum(latencies) / len(latencies), 2) if latencies else 0.0,
        },
    }


def _load_prompts(dataset_path: str, seed: int | None = None) -> list[dict]:
    """Read the JSONL dataset, optionally applying a deterministic permutation."""
    with open(dataset_path, encoding="utf-8") as f:
        items = [json.loads(line) for line in f if line.strip()]
    if seed is not None:
        random.Random(seed).shuffle(items)
    return items


def _build_run_config(
    router: SelfEvolvingRouter,
    dataset_path: str,
    permutation_seed: int | None,
    seed_set_name: str | None,
) -> dict:
    """Provenance block: everything needed to reproduce (or compare) this run."""
    return {
        "proposer_mode": router.proposer_mode,
        "few_shot": router.few_shot,
        "threshold": router.threshold,
        "batch_size": router.batch_size,
        "max_reroutes": MAX_REROUTES,
        "max_categories": getattr(router.registry, "_max", 30),
        "seed_set_name": seed_set_name,
        "seed_set_hash": _seed_set_hash(router.initial_categories),
        "dataset_path": dataset_path,
        "dataset_hash": _file_sha1(dataset_path),
        "permutation_seed": permutation_seed,
        "temperature": getattr(router.proposer, "temperature", None),
        "temperature_requested": getattr(router.proposer, "temperature_requested", None),
        "laya_model": router.laya_model,
        "backend": router.backend,
        "proposer_model": _proposer_model(router.proposer),
        "git_sha": _git_sha(),
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }


def _seed_set_hash(initial_categories: list[dict]) -> str | None:
    """SHA-1 of the seeded (name, description) list; None for a cold start."""
    if not initial_categories:
        return None
    canonical = json.dumps([[c.get("name"), c.get("description")] for c in initial_categories])
    return hashlib.sha1(canonical.encode("utf-8")).hexdigest()


def _file_sha1(path: str) -> str | None:
    try:
        with open(path, "rb") as f:
            return hashlib.sha1(f.read()).hexdigest()
    except OSError:
        return None


def _proposer_model(proposer) -> str | None:
    """The configured OpenAI (primary) model, read defensively from the proposer."""
    primary = getattr(proposer, "_primary", None)
    if isinstance(primary, dict):
        return primary.get("model")
    return None


def _git_sha() -> str | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
        if out.returncode == 0:
            return out.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None
    return None


def _retry_pending(
    router: SelfEvolvingRouter,
    pending: list[dict],
    step: int,
    events: list[dict],
    retries: dict[str, int],
    max_reroutes: int,
) -> list[dict]:
    """Re-classify pending 'other' prompts; cap retries to avoid churn."""
    survivors = []
    for ev in pending:
        if retries.get(ev["id"], 0) >= max_reroutes:
            continue  # retry budget exhausted: accepted as permanent 'other'
        retries[ev["id"]] = retries.get(ev["id"], 0) + 1
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
