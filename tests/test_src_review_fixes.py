"""Regression tests for src/laya_router review fixes (no Laya model, no network)."""

import json

import pytest

from laya_router import llm
from laya_router.categories import CategoryRegistry
from laya_router.cli import _load_seed_categories
from laya_router.llm import LLMCategoryProposer, ProposedCategory
from laya_router.simulation import _load_prompts


# -- proposer parsing: decoy arrays --------------------------------------------
def test_parse_skips_decoy_array_before_real_proposals():
    text = (
        'Avoid names like ["misc", "other"]. Proposals:\n'
        '[{"name": "translation", "description": "Converting text between languages."}]'
    )
    out = LLMCategoryProposer._parse(text)
    assert out == [ProposedCategory("translation", "Converting text between languages.")]


def test_parse_only_decoys_still_returns_without_raising():
    # Greedy span "[...] and [..." is not valid JSON; the first parsed decoy wins.
    out, drops = LLMCategoryProposer._parse_with_drops('Nope: ["misc"] and [] then [oops')
    assert out == []
    assert drops == [{"name": None, "reason": "not_dict"}]


# -- env config: blank values fall back to defaults ------------------------------
def test_load_providers_blank_env_values_use_defaults(monkeypatch):
    monkeypatch.setattr(llm, "load_dotenv", lambda *a, **k: False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    for var in ("OPENAI_BASE_URL", "OPENAI_MODEL", "LMSTUDIO_BASE_URL", "LMSTUDIO_MODEL"):
        monkeypatch.setenv(var, "")
    proposer = llm.load_providers()
    assert proposer._primary["base_url"] == "https://api.openai.com/v1"
    assert proposer._primary["model"] == "gpt-5.6-luna"
    assert proposer._fallback == {"base_url": "http://localhost:1234/v1", "model": "qwen2.5-7b-instruct"}


# -- dataset loading: malformed line reports its location -----------------------
def test_load_prompts_reports_bad_line_number(tmp_path):
    ds = tmp_path / "d.jsonl"
    ds.write_text('{"id": "a", "text": "x", "ground_truth": "g"}\n\n{broken\n', encoding="utf-8")
    with pytest.raises(ValueError, match=r"d\.jsonl:3"):
        _load_prompts(str(ds))


# -- seed file: non-string fields rejected up front -----------------------------
def test_seed_file_rejects_non_string_fields(tmp_path):
    path = tmp_path / "seeds.json"
    path.write_text(json.dumps([{"name": None, "description": "x"}]), encoding="utf-8")
    with pytest.raises(ValueError, match="string"):
        _load_seed_categories(str(path))


# -- registry: shared gate keeps rejection records and ownership ----------------
def test_registry_add_and_seed_rejection_records_match():
    reg = CategoryRegistry(max_categories=2, extra_dedup="token_jaccard_025")
    assert reg.seed("translation", "Converting text between languages.") is not None
    reg.seed("translations", "x", step=0, source_ids=("s1",))
    reg.add("language_translation_help", "Converting text between languages.", 3, ["p1"])
    assert reg.seed_rejections == [
        {"name": "translations", "reason": "duplicate", "rule": "substring", "step": 0, "source_ids": ["s1"]}
    ]
    assert reg.rejections == [
        {"name": "language_translation_help", "reason": "duplicate", "rule": "substring",
         "step": 3, "source_ids": ["p1"]}
    ]
    ids = ["p2"]
    cat = reg.add("cooking", "Recipes and meal preparation.", 4, ids)
    ids.append("mutated")
    assert cat is not None and cat.created_from == ["p2"]
    reg.add("fitness", "Workouts.", 5, ["p3"])
    assert reg.rejections[-1]["reason"] == "cap"
