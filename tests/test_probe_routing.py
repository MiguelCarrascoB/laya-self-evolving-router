import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("probe", Path(__file__).parents[1] / "scripts/probe_routing.py")
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


def test_registry_order_and_subsets():
    assert [x["name"] for x in probe.select_registry("perfect", 4)] == [x[0] for x in probe.CANONICAL[:4]]
    full = probe.select_registry("perfect", 20)
    assert [x["name"] for x in full[10:]] == sorted(probe.NOVEL)
    discovered = [{"name": "b", "description": ""}, {"name": "a", "description": ""}]
    assert probe.select_registry("discovered", 1, discovered)[0]["name"] == "b"


def row(choice, truth="x", confidence=.4, top=.4, margin=.2):
    return {"choice": choice, "ground_truth": truth, "confidence": confidence, "top_prob": top, "top2_margin": margin, "input_tokens": 10}


def test_metrics_and_gates():
    rows = [row("x", "x", .4, .4, .2), row("other", "y", .9, .9, .8), row("z", "novel_z", .6, .95, .7)]
    m = probe.compute_metrics(rows, 6)
    assert m["accuracy_exact"] == 1 / 3
    assert m["accuracy_stripped"] == 2 / 3
    assert m["other_rate"] == 1 / 3
    assert m["gate_entropy0.5"] == .5 and m["gate_topprob0.5"] == .5 and m["gate_topprob0.9"] == .5
    assert m["mean_top2_margin"] == (.2 + .8 + .7) / 3


def test_bucket_boundaries_and_one_option_margin():
    assert [probe.bucket(x) for x in (2, 3, 5, 6, 10, 11, 30)] == ["2", "3-5", "3-5", "6-10", "6-10", "11+", "11+"]
    assert probe.top2_margin({"other": .7}) == 0
    assert probe.top2_margin({}) == 0


def test_output_shape():
    route = row("x", "x")
    route["id"] = "p1"
    c = probe.assemble_config("perfect", 1, "full", [route])
    assert set(("family", "k", "policy", "n_options", "routes", "accuracy_exact")) <= c.keys()
    assert c["n_options"] == 2 and c["routes"][0]["id"] == "p1"
