import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("replay_precheck", Path(__file__).parents[1] / "scripts/replay_precheck.py")
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
build_snapshots = _module.build_snapshots
extract_batches = _module.extract_batches
overlap_flag = _module.overlap_flag
probe_variants = _module.probe_variants
token_jaccard = _module.token_jaccard


def test_extract_first_pass_and_partial_batch():
    events = [{"text": str(i), "route": "other", "ground_truth": "x", "rerouted": i == 1} for i in range(12)]
    out = extract_batches({"events": events}, batch_size=5)
    assert out["selected_count"] == 11
    assert [len(b["events"]) for b in out["batches"]] == [5, 5, 1]
    assert out["partial_batch"] is True


def test_snapshot_prefix_and_shape_defensive():
    results = {"category_creations": [{"name": "a", "description": "A"}, {"name": "b", "description": "B"}],
               "registry_final": {"categories": ["a", "b"]}}
    out = build_snapshots(results, at=(0, 1, 3))
    assert [c["name"] for c in out["k=1"]] == ["a"]
    assert out["k=3"] if "k=3" in out else True


def test_jaccard_synonym_and_unrelated():
    assert token_jaccard("travel_planning trip itineraries", "travel_logistics trip itineraries") >= .25
    assert not overlap_flag("gift_ideas", "Suggest gifts", [{"name": "scheduling", "description": "Planning tasks across time"}])


def test_variant_probe_math():
    existing = [{"name": "travel_planning", "description": "trip itineraries"}]
    proposals = [{"name": "travel_logistics", "description": "trip itineraries", "existing": existing,
                  "has_similar": False, "token_overlap": True},
                 {"name": "gift_ideas", "description": "Suggest gifts", "existing": existing,
                  "has_similar": False, "token_overlap": False}]
    out = probe_variants(proposals)
    assert out["none"]["blocked"] == 0 and out["none"]["missed"] == 1
    assert out["token_jaccard_025"]["blocked"] == 1 and out["token_jaccard_025"]["tp_proxy"] == 1
