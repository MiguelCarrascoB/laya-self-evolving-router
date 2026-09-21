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
