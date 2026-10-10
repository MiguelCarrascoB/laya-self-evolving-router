"""Pure math tests for metrics.compute_metrics (no Laya / no router import)."""

from laya_evolve.metrics import compute_metrics, demotes_to_other, gate_thresholds


def test_frozen_gate_preserves_strict_historical_check():
    assert demotes_to_other(choice="x", probabilities={}, confidence=0.49, gate="frozen") == (True, "low_confidence")
    assert demotes_to_other(choice="x", probabilities={}, confidence=0.5, gate="frozen") == (False, "")
    assert demotes_to_other(choice="other", probabilities={}, confidence=0.0, gate="frozen") == (False, "")


def test_bucket_topprob_boundaries():
    ten = {str(i): 0.0 for i in range(9)}
    eleven = {str(i): 0.0 for i in range(10)}
    ten["x"] = 0.5
    eleven["x"] = 0.9
    assert demotes_to_other(choice="x", probabilities=ten, confidence=0.0, gate="bucket-topprob") == (False, "")
    assert demotes_to_other(choice="x", probabilities=eleven, confidence=0.0, gate="bucket-topprob") == (False, "")
    ten["x"] = 0.49
    eleven["x"] = 0.89
    assert demotes_to_other(choice="x", probabilities=ten, confidence=1.0, gate="bucket-topprob")[0]
    assert demotes_to_other(choice="x", probabilities=eleven, confidence=1.0, gate="bucket-topprob")[0]


def test_bucket_gate_safe_other_and_empty_probabilities():
    assert demotes_to_other(choice="other", probabilities={"other": 0.0}, confidence=0.0, gate="bucket-topprob") == (False, "")
    assert demotes_to_other(choice="x", probabilities={}, confidence=0.0, gate="bucket-topprob") == (False, "")


def test_gate_threshold_shapes():
    assert gate_thresholds("bucket-topprob", 0.5) == {"<=10 options": 0.5, "11+ options": 0.9}
    assert gate_thresholds("frozen", 0.7) == {"frozen threshold": 0.7}


def _cat(name, seeded=False):
    return {
        "name": name,
        "description": name,
        "created_at_step": 0 if seeded else 5,
        "created_from": [] if seeded else ["p1"],
        "seeded": seeded,
    }


def test_last_decision_wins_dedup():
    events = [
        {"id": "a", "ground_truth": "scheduling", "route": "other", "reason": "other_bucket", "correct": False},
        {"id": "a", "ground_truth": "scheduling", "route": "scheduling", "reason": "classified", "correct": True},
    ]
    m = compute_metrics(events, [], {"scheduling"}, [])
    assert m["accuracy_final"] == 1.0
    assert m["coverage_final"] == 1.0
    assert m["re_route_count"] == 1


def test_novel_absorbed():
    events = [
        {"id": "n1", "ground_truth": "novel_x", "route": "novel_x", "reason": "classified", "correct": True},
        {"id": "n2", "ground_truth": "novel_y", "route": "other", "reason": "other_bucket", "correct": False},
        {"id": "n3", "ground_truth": "novel_z", "route": "other", "reason": "other_bucket", "correct": False},
    ]
    m = compute_metrics(events, [], set(), [])
    assert m["novel_prompts"] == 3
    assert m["novel_final_other"] == 2
    assert m["novel_absorbed"] == 1


def test_reason_split_counts():
    events = [
        {"id": "a", "ground_truth": "scheduling", "route": "scheduling", "reason": "classified", "correct": True},
        {"id": "b", "ground_truth": "novel_y", "route": "other", "reason": "other_bucket", "correct": False},
        {"id": "c", "ground_truth": "novel_z", "route": "other", "reason": "low_confidence", "correct": False},
        {"id": "d", "ground_truth": "scheduling", "route": "other", "reason": "low_confidence", "correct": False},
    ]
    m = compute_metrics(events, [], {"scheduling"}, [])
    assert m["other_bucket_final"] == 1
    assert m["low_confidence_final"] == 2
    assert m["other_rate_final"] == round(3 / 4, 4)


def test_births_beyond_seeds_and_seed_count():
    registry = [_cat("scheduling", seeded=True), _cat("coding_help"), _cat("travel_planning")]
    m = compute_metrics([], registry, {"scheduling"}, [])
    assert m["seed_count"] == 1
    assert m["births_beyond_seeds"] == 2
    assert m["discovery_slots_used"] == 2
    assert m["registry_size_final"] == 3


def test_label_match_zero_covered():
    events = [
        {"id": "a", "ground_truth": "scheduling", "route": "other", "reason": "other_bucket", "correct": False},
        {"id": "b", "ground_truth": "novel_y", "route": "other", "reason": "other_bucket", "correct": False},
    ]
    m = compute_metrics(events, [], {"scheduling"}, [])
    assert m["coverage_final"] == 0.0
    assert m["label_match_rate_of_covered"] == 0.0


def test_empty_events():
    m = compute_metrics([], [], set(), [])
    assert m["accuracy_final"] == 0
    assert m["coverage_final"] == 0
    assert m["novel_prompts"] == 0
    assert m["novel_absorbed"] == 0


def test_seed_categories_recovered_continuity():
    registry = [_cat("scheduling", seeded=True), _cat("coding_help")]
    seeded = {"scheduling", "coding_help", "translation"}
    m = compute_metrics([], registry, seeded, [])
    assert m["seed_categories_recovered"] == round(2 / 3, 4)
    assert m["seed_categories_recovered_note"] == "trivial under seeded runs"


def test_rejected_proposals_by_reason():
    rejections = [
        {"name": "foo", "reason": "duplicate", "step": 3, "source_ids": []},
        {"name": "bar", "reason": "cap", "step": 4, "source_ids": []},
        {"name": "baz", "reason": "duplicate", "step": 5, "source_ids": []},
    ]
    m = compute_metrics([], [], set(), rejections)
    assert m["rejected_proposals"] == {"total": 3, "duplicate": 2, "cap": 1}
