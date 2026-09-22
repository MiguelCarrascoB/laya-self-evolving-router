"""Run metrics computed from a simulation's events and final registry.

Pure functions: no imports from the Laya model stack, so CI can compute metrics
on Linux without ``laya-mlx`` / ``laya-coreml`` (and without importing the
router). The pre-existing metric definitions replicate the values previously
produced by ``simulation._summary_metrics`` exactly, so the metric names stay
byte-compatible for the README and visualizer.
"""

from __future__ import annotations

OTHER = "other"


def compute_metrics(
    events: list[dict],
    registry_dicts: list[dict],
    seeded: set[str],
    rejections: list[dict] | None = None,
) -> dict:
    """Compute final run metrics from the event log and registry state.

    ``events`` is the full event log (first-pass plus re-routes); the last
    routing decision per prompt id wins. ``registry_dicts`` is the output of
    ``CategoryRegistry.as_dicts()``. ``seeded`` is the set of ground-truth
    labels for seeded intents (anything not starting with ``novel``).
    ``rejections`` is ``CategoryRegistry.rejections``.
    """
    rejections = rejections or []

    final: dict[str, dict] = {}
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

    registry_names = {d["name"] for d in registry_dicts}
    seeded_entries = [d for d in registry_dicts if d.get("seeded")]
    discovered_entries = [d for d in registry_dicts if not d.get("seeded")]

    rejected = {"total": 0, "duplicate": 0, "cap": 0}
    for r in rejections:
        rejected["total"] += 1
        reason = r.get("reason")
        if reason in rejected:
            rejected[reason] += 1

    novel_prompts = len(handled_ground_truth)
    novel_final_other = len(novel_other)

    return {
        "accuracy_final": round(correct / n, 4) if n else 0,  # exact label match
        "coverage_final": round((n - routed_other) / n, 4) if n else 0,  # routed to a real category
        "label_match_rate_of_covered": round(
            correct / (n - routed_other), 4
        ) if routed_other < n else 0.0,
        "other_rate_final": round(routed_other / n, 4) if n else 0,
        "novel_prompts": novel_prompts,
        "novel_final_other": novel_final_other,
        "novel_absorbed": novel_prompts - novel_final_other,
        "seed_categories_recovered": round(len(registry_names & seeded) / len(seeded), 4) if seeded else 0,
        "seed_categories_recovered_note": "trivial under seeded runs",
        "re_route_count": len(events) - len(final_events),
        "seed_count": len(seeded_entries),
        "births_beyond_seeds": len(discovered_entries),
        "discovery_slots_used": len(discovered_entries),
        "registry_size_final": len(registry_dicts),
        "other_bucket_final": sum(1 for e in final_events if e["reason"] == "other_bucket"),
        "low_confidence_final": sum(1 for e in final_events if e["reason"] == "low_confidence"),
        "rejected_proposals": rejected,
    }
