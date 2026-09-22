#!/usr/bin/env python3
"""Offline proposer replay and deduplication pre-check.

The replay deliberately exercises only the category proposer; routing and result
files are inputs, never modified.  Network access is needed only by ``main``.
"""
from __future__ import annotations

import argparse
import json
import random
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from laya_router.categories import CategoryRegistry
from laya_router.llm import load_providers

MODES = ("blind", "as-today", "hardened", "system-placement")


def _category_dicts(categories: Any, descriptions: dict[str, str] | None = None) -> list[dict]:
    descriptions = descriptions or {}
    out = []
    for item in categories or []:
        if isinstance(item, dict):
            name = str(item.get("name", ""))
            desc = str(item.get("description", descriptions.get(name, "")))
        else:
            name = str(item)
            desc = descriptions.get(name, "")
        if name:
            out.append({"name": name, "description": desc})
    return out


def extract_batches(results: dict, batch_size: int = 10) -> dict:
    """Extract first-pass ``other`` prompts, retaining a final partial batch."""
    selected = [
        e for e in results.get("events", [])
        if not e.get("rerouted") and e.get("route") == "other"
    ]
    batches = []
    for start in range(0, len(selected), batch_size):
        events = selected[start:start + batch_size]
        batches.append({
            "id": len(batches),
            "events": events,
            "prompts": [str(e.get("text", "")) for e in events],
            "ground_truth": dict(Counter(str(e.get("ground_truth", "")) for e in events)),
            "partial": len(events) < batch_size,
        })
    return {"batches": batches, "selected_count": len(selected),
            "partial_batch": bool(batches and batches[-1]["partial"])}


def build_snapshots(results: dict, at=(0, 10, 20, 30)) -> dict[str, list[dict]]:
    """Build creation-prefix and seed taxonomy snapshots."""
    creations = results.get("category_creations", [])
    desc_by_name = {str(c.get("name")): str(c.get("description", "")) for c in creations}
    final = results.get("registry_final", {})
    final_categories = final.get("categories", []) if isinstance(final, dict) else []
    # Names-only final registries are common in historical files.  The creation
    # list is the authoritative description source for those names.
    if isinstance(final_categories, list):
        desc_by_name.update({x["name"]: x["description"] for x in _category_dicts(final_categories, desc_by_name)})
    snapshots: dict[str, list[dict]] = {}
    for k in at:
        if k <= len(creations):
            snapshots[f"k={k}"] = _category_dicts(creations[:k], desc_by_name)
    root = Path(__file__).resolve().parents[1]
    for label, filename in (("seeds-canonical", "data/seeds_canonical.json"),
                            ("seeds-imperfect", "data/seeds_imperfect.json")):
        with (root / filename).open() as fh:
            snapshots[label] = _category_dicts(json.load(fh))
    return snapshots


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower().replace("_", " ")))


def token_jaccard(left: str, right: str) -> float:
    a, b = _tokens(left), _tokens(right)
    return len(a & b) / len(a | b) if a and b else 0.0


def overlap_flag(name: str, description: str, existing: list[dict], threshold: float = 0.25) -> bool:
    text = f"{name} {description}"
    return any(token_jaccard(text, f"{c.get('name', '')} {c.get('description', '')}") >= threshold
               for c in existing)


def _has_similar(name: str, existing: list[dict]) -> bool:
    reg = CategoryRegistry()
    for c in existing:
        reg.add(c["name"], c.get("description", ""), 0, [])
    return reg.has_similar(name)


def probe_variants(proposals: list[dict], embeddings: dict[str, list[float]] | None = None) -> dict:
    """Return dedup variant counts for already-judged proposal records."""
    variants = ("none", "current", "token_jaccard_025", "token_jaccard_04", "embedding_cosine_085")
    out = {v: {"blocked": 0, "tp_proxy": 0, "over_blocking": 0, "missed": 0,
               "status": "available"} for v in variants}
    truth = lambda p: bool(p.get("has_similar") or p.get("token_overlap"))
    for p in proposals:
        existing = p.get("existing", [])
        text = f"{p.get('name', '')} {p.get('description', '')}"
        checks = {
            "none": False,
            "current": bool(p.get("has_similar")),
            "token_jaccard_025": bool(p.get("token_overlap")),
            "token_jaccard_04": any(token_jaccard(text, f"{c.get('name', '')} {c.get('description', '')}") >= .4 for c in existing),
            "embedding_cosine_085": _cosine_match(text, existing, embeddings, .85),
        }
        for variant, blocked in checks.items():
            if blocked:
                out[variant]["blocked"] += 1
                if p.get("token_overlap"):
                    out[variant]["tp_proxy"] += 1
                else:
                    out[variant]["over_blocking"] += 1
            elif truth(p):
                out[variant]["missed"] += 1
    return out


def _cosine_match(text: str, existing: list[dict], embeddings: dict[str, list[float]] | None, threshold: float) -> bool:
    if not embeddings or text not in embeddings:
        return False
    import math
    a = embeddings[text]
    for c in existing:
        b = embeddings.get(f"{c.get('name', '')} {c.get('description', '')}")
        if not b:
            continue
        denom = math.sqrt(sum(x*x for x in a) * sum(x*x for x in b))
        if denom and sum(x*y for x, y in zip(a, b)) / denom >= threshold:
            return True
    return False


def _embedding_map(proposer, texts: list[str]) -> tuple[dict[str, list[float]], str]:
    try:
        response = proposer._client.embeddings.create(model="text-embedding-3-small", input=texts)
        return {text: list(item.embedding) for text, item in zip(texts, response.data)}, "available"
    except Exception as exc:  # endpoint availability is an expected limitation
        return {}, f"unavailable: {type(exc).__name__}: {exc}"


def run_replay(results: dict, proposer, max_calls: int = 36, seed: int = 0) -> dict:
    extracted = extract_batches(results)
    snapshots = build_snapshots(results)
    keys = [k for k in ("k=0", "k=10", "k=30") if k in snapshots]
    rng = random.Random(seed)
    batches = extracted["batches"][:]
    if len(batches) > 3:
        batches = rng.sample(batches, 3)
        batches.sort(key=lambda b: b["id"])
    calls = 0
    proposals: list[dict] = []
    call_records: list[dict] = []
    mode_stats = {m: {"proposals": 0, "empty": 0, "parse_failures": 0, "has_similar_rejected": 0, "overlap_flagged": 0} for m in MODES}
    for snapshot_key in keys:
        existing = snapshots[snapshot_key]
        for batch in batches:
            for mode in MODES:
                if calls >= max_calls:
                    break
                before = dict(proposer.stats)
                try:
                    returned = proposer.propose(batch["prompts"], existing, mode=mode, few_shot="none")
                except Exception as exc:
                    returned = []
                    error = f"{type(exc).__name__}: {exc}"
                else:
                    error = None
                calls += 1
                stats = mode_stats[mode]
                stats["empty"] += int(not returned)
                parse_delta = proposer.stats.get("parse_failures", 0) - before.get("parse_failures", 0)
                stats["parse_failures"] += parse_delta
                call_records.append({"mode": mode, "batch_id": batch["id"], "snapshot": snapshot_key,
                                     "returned_empty": not returned, "parse_failures": parse_delta,
                                     "error": error})
                for item in returned:
                    name, description = item.name, item.description
                    similar = _has_similar(name, existing)
                    overlap = overlap_flag(name, description, existing)
                    record = {"name": name, "description": description, "mode": mode,
                              "batch_id": batch["id"], "snapshot": snapshot_key,
                              "existing": existing, "has_similar": similar,
                              "token_overlap": overlap}
                    if error:
                        record["error"] = error
                    proposals.append(record)
                    stats["proposals"] += 1
                    stats["has_similar_rejected"] += int(similar)
                    stats["overlap_flagged"] += int(overlap)
    texts = [f"{p['name']} {p['description']}" for p in proposals]
    for p in proposals:
        for c in p["existing"]:
            texts.append(f"{c.get('name', '')} {c.get('description', '')}")
    embeddings, embedding_status = _embedding_map(proposer, list(dict.fromkeys(texts))) if proposals else ({}, "available")
    variants = probe_variants(proposals, embeddings)
    variants["embedding_cosine_085"]["status"] = embedding_status
    return {"calls": calls, "max_calls": max_calls, "seed": seed, "batches": extracted,
            "snapshots": snapshots, "selected_snapshots": keys, "modes": mode_stats,
            "call_records": call_records, "proposals": proposals, "dedup_variants": variants,
            "embedding_status": embedding_status,
            "registry_final_categories_shape": type(results.get("registry_final", {}).get("categories", [])).__name__}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="results/replay/precheck.json")
    parser.add_argument("--max-calls", type=int, default=36)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--input", default="results/results-v3-full.json")
    args = parser.parse_args()
    with open(args.input) as fh:
        results = json.load(fh)
    proposer = load_providers()
    report = run_replay(results, proposer, min(args.max_calls, 36), args.seed)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w") as fh:
        json.dump(report, fh, indent=2)
    print("| mode | proposals | []-rate | has_similar-rejected | overlap-flagged | parse-failures |")
    print("|---|---:|---:|---:|---:|---:|")
    for mode, s in report["modes"].items():
        calls = sum(1 for c in report["call_records"] if c["mode"] == mode)
        print(f"| {mode} | {s['proposals']} | {s['empty'] / calls:.1%} | {s['has_similar_rejected']} | {s['overlap_flagged']} | {s['parse_failures']} |")
    print("\n| dedup variant | blocked | TP-proxy | missed |")
    print("|---|---:|---:|---:|")
    for variant, s in report["dedup_variants"].items():
        print(f"| {variant} | {s['blocked']} | {s['tp_proxy']} | {s['missed']} |")


if __name__ == "__main__":
    main()
