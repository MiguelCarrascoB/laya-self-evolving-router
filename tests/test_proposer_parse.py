"""Parse tests for LLMCategoryProposer._parse (pure function, no Laya/LLM needed).

These tests exercise the response-parsing logic in isolation so CI can run on
Linux without importing ``laya_mlx`` or hitting any network endpoint.
"""

from laya_router.llm import LLMCategoryProposer, ProposedCategory


def test_parse_direct_json_array():
    out = LLMCategoryProposer._parse(
        '[{"name": "translation", "description": "Converting text between languages."}]'
    )
    assert out == [ProposedCategory("translation", "Converting text between languages.")]


def test_parse_embedded_json_array_with_preamble():
    text = (
        "Here are my proposals:\n"
        '[{"name": "coding_help", "description": "Debugging and refactoring code."}, '
        '{"name": "travel_planning", "description": "Planning trips and itineraries."}]'
    )
    out = LLMCategoryProposer._parse(text)
    assert [c.name for c in out] == ["coding_help", "travel_planning"]


def test_parse_empty_array():
    assert LLMCategoryProposer._parse("[]") == []


def test_parse_rejects_malformed():
    import pytest

    with pytest.raises(ValueError):
        LLMCategoryProposer._parse("not a json array at all")


def test_parse_skips_items_without_description():
    out = LLMCategoryProposer._parse(
        '[{"name": "foo"}, {"name": "bar", "description": "A real intent"}]'
    )
    assert out == [ProposedCategory("bar", "A real intent")]


def test_parse_skips_non_dict_items():
    out = LLMCategoryProposer._parse('[null, "not an object", {"name": "ok", "description": " fine "}]')
    assert out == [ProposedCategory("ok", "fine")]


def test_parse_strips_name_and_description_whitespace():
    out = LLMCategoryProposer._parse(
        '[{"name": "  scheduling  ", "description": "  Planning tasks  "}]'
    )
    assert out == [ProposedCategory("scheduling", "Planning tasks")]


def test_parse_records_long_description_drop():
    text = '[{"name": "too_long", "description": "one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen"}]'
    out, drops = LLMCategoryProposer._parse_with_drops(text)
    assert out == []
    assert drops == [{"name": "too_long", "reason": "desc_too_long"}]
