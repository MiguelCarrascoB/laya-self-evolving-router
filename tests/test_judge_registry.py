import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))
from scripts.judge_registry import (  # noqa: E402
    GROUND_TRUTH_LABELS,
    _fragmentation,
    _parse_judge_response,
    _summary,
    build_system_prompt,
)


def test_parse_well_formed_and_preamble():
    result = _parse_judge_response('Here is the audit:\n{"mapping":[{"name":"a","mapped_to":"coding_help","why":"x"}],"dup_pairs":[{"a":"a","b":"b","borderline":false,"why":"same"}],"notes":"ok"}')
    assert result["mapping"][0]["mapped_to"] == "coding_help"
    assert result["dup_pairs"][0]["borderline"] is False


def test_parse_malformed_and_wrong_types_never_crashes():
    assert _parse_judge_response("not json")["_warnings"]
    result = _parse_judge_response('{"mapping":"bad","dup_pairs":[{"a":"x","b":"y","borderline":"no"}]}')
    assert result["mapping"] == [] and result["dup_pairs"] == []
    assert result["_warnings"]


def test_fragmentation_and_summary():
    mapping = [
        {"name": "a", "mapped_to": "coding_help"},
        {"name": "b", "mapped_to": "coding_help"},
        {"name": "c", "mapped_to": "coding_help"},
        {"name": "d", "mapped_to": "junk"},
        {"name": "e", "mapped_to": "unclear"},
    ]
    pairs = [{"a": "a", "b": "b", "borderline": False}, {"a": "c", "b": "d", "borderline": True}]
    assert _fragmentation(mapping) == {"coding_help": 3}
    summary = _summary(5, mapping, pairs)
    assert summary["n_mapped"] == 3
    assert summary["n_junk"] == 1 and summary["n_unclear"] == 1
    assert summary["dup_pair_count"] == 2 and summary["dup_pair_count_strict"] == 1
    assert summary["fragmentation_max"] == 3


def test_prompt_contains_policy_and_all_labels():
    prompt = build_system_prompt()
    for sentence in (
        "same scope, interchangeable",
        "borderline = arguable",
        "Narrower-but-distinct sub-intents are NOT dups",
        "traffic split across several narrower-but-distinct categories",
        '"junk"',
        '"unclear"',
    ):
        assert sentence in prompt
    for label in GROUND_TRUTH_LABELS:
        assert label in prompt
