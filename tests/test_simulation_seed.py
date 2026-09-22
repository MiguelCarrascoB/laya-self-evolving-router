"""Permutation determinism and run provenance for the simulation (no Laya load)."""

import json

from laya_router.simulation import _load_prompts, _seed_set_hash, run_simulation


def _write_dataset(path, prompts):
    with open(path, "w", encoding="utf-8") as f:
        for p in prompts:
            f.write(json.dumps(p) + "\n")


def _items(n):
    return [{"id": f"p{i}", "text": f"t{i}", "ground_truth": "scheduling"} for i in range(n)]


# -- permutation determinism (pure _load_prompts) ----------------------------

def test_no_seed_preserves_input_order(tmp_path):
    ds = tmp_path / "d.jsonl"
    items = _items(20)
    _write_dataset(ds, items)
    out = _load_prompts(str(ds), None)
    assert [p["id"] for p in out] == [p["id"] for p in items]


def test_same_seed_same_order(tmp_path):
    ds = tmp_path / "d.jsonl"
    _write_dataset(ds, _items(20))
    a = _load_prompts(str(ds), 42)
    b = _load_prompts(str(ds), 42)
    assert [p["id"] for p in a] == [p["id"] for p in b]


def test_different_seeds_differ(tmp_path):
    ds = tmp_path / "d.jsonl"
    _write_dataset(ds, _items(50))
    a = _load_prompts(str(ds), 1)
    b = _load_prompts(str(ds), 2)
    assert [p["id"] for p in a] != [p["id"] for p in b]


# -- run provenance via a stub router ----------------------------------------

class _FakeProposer:
    stats = {"calls": 0, "attempts": 0, "fallback_calls": 0,
             "empty_responses": 0, "parse_failures": 0, "parse_drops": []}
    batch_size = 10
    temperature = 0.0

    def __init__(self, model="gpt-test"):
        self._primary = {"model": model}
        self._fallback = {"model": "lm-test"}


class _FakeRegistry:
    def __init__(self):
        self.rejections = []
        self.seed_rejections = []
        self._max = 30

    def as_dicts(self):
        return []

    def growth_history(self):
        return []

    def is_full(self):
        return False

    def names(self):
        return []


class _FakeRouter:
    def __init__(self, model="fake/laya-model", initial_categories=None):
        self.backend = "mlx"
        self.threshold = 0.5
        self.llm_calls = 0
        self.laya_model = model
        self.proposer_mode = "as-today"
        self.few_shot = None
        self.batch_size = 10
        self.initial_categories = list(initial_categories or [])
        self.proposer = _FakeProposer()
        self.registry = _FakeRegistry()

    def route(self, prompt_id, text, step):
        return {
            "id": prompt_id, "text": text,
            "laya_choice": "scheduling", "route": "scheduling", "reason": "classified",
            "probs": {"scheduling": 0.9, "other": 0.1},
            "top_prob": 0.9, "top2_margin": 0.8, "n_options": 2,
            "latency_ms": 1.0, "input_tokens": 0, "categories_at_route": 0,
        }

    def learn_from_others(self, others, step):
        return []

    def stats(self):
        return {"backend": self.backend, "categories": [], "llm_calls": self.llm_calls}


def test_run_simulation_provenance(tmp_path):
    ds = tmp_path / "d.jsonl"
    items = _items(5)
    _write_dataset(ds, items)
    results = run_simulation(_FakeRouter(model="fake/laya-model"), str(ds), seed=7, seed_set_name="seeds.json")

    # meta.model bug fix: the Laya model id, not the backend string.
    assert results["meta"]["model"] == "fake/laya-model"
    assert results["meta"]["proposer_model"] == "gpt-test"
    assert results["meta"]["backend"] == "mlx"

    rc = results["run_config"]
    assert rc["permutation_seed"] == 7
    assert rc["seed_set_name"] == "seeds.json"
    assert rc["seed_set_hash"] is None
    assert rc["proposer_mode"] == "as-today"
    assert rc["laya_model"] == "fake/laya-model"
    assert rc["backend"] == "mlx"
    assert rc["max_categories"] == 30
    assert rc["max_reroutes"] == 2
    assert rc["batch_size"] == 10
    assert rc["threshold"] == 0.5
    assert rc["temperature"] == 0.0
    assert rc["dataset_path"] == str(ds)
    assert len(rc["dataset_hash"]) == 40
    assert rc["few_shot"] is None

    for key in ("meta", "run_config", "events", "category_creations",
                "registry_final", "seed_rejections", "growth_history", "metrics", "latency"):
        assert key in results

    # events follow the seeded permutation order
    expected_ids = [p["id"] for p in _load_prompts(str(ds), 7)]
    assert [e["id"] for e in results["events"]] == expected_ids


def test_run_simulation_seed_hash(tmp_path):
    ds = tmp_path / "d.jsonl"
    _write_dataset(ds, _items(1))
    cats = [{"name": "scheduling", "description": "Planning tasks"}]

    seeded = run_simulation(_FakeRouter(initial_categories=cats), str(ds), seed_set_name="seeds.json")
    assert seeded["run_config"]["seed_set_hash"] == _seed_set_hash(cats)
    assert seeded["run_config"]["seed_set_name"] == "seeds.json"

    cold = run_simulation(_FakeRouter(), str(ds))
    assert cold["run_config"]["seed_set_hash"] is None
    assert cold["run_config"]["seed_set_name"] is None


def test_seed_set_hash_helper():
    assert _seed_set_hash([]) is None
    assert _seed_set_hash([{"name": "a", "description": "b"}]) == _seed_set_hash(
        [{"name": "a", "description": "b"}]
    )
