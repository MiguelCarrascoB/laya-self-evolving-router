from laya_router.llm import (
    FEWSHOT_EXAMPLES,
    PROMPT_TEMPLATE,
    SYSTEM_PROMPT_NO_FEWSHOT,
    SYSTEM_PROMPT_TEMPLATE,
    build_system_prompt,
    build_user_prompt,
)


EXISTING = [{"name": "translation", "description": "Converting text between languages."}]
PROMPTS = ["translate this", "translate that"]


def expected_system(few_shot):
    if few_shot == "none":
        return SYSTEM_PROMPT_NO_FEWSHOT
    n = 3 if few_shot in ("three", "3") else len(FEWSHOT_EXAMPLES)
    examples = "\n".join(f'- "{name}" — {desc}' for name, desc in FEWSHOT_EXAMPLES[:n])
    return SYSTEM_PROMPT_TEMPLATE.format(examples=examples)


def expected_user():
    return PROMPT_TEMPLATE.format(
        existing="- translation: Converting text between languages.",
        prompts="\n".join(PROMPTS),
    )


def test_as_today_is_byte_identical_for_each_few_shot_value():
    for few_shot in ("full", "three", "none", "3"):
        assert build_system_prompt(existing=EXISTING, mode="as-today", few_shot=few_shot) == expected_system(few_shot)
        assert build_user_prompt(PROMPTS, EXISTING, mode="as-today") == expected_user()


def test_blind_has_no_registry_content():
    prompt = build_user_prompt(PROMPTS, EXISTING, mode="blind")
    assert "Existing categories" not in prompt
    assert "Do not near-duplicate" not in prompt


def test_hardened_adds_overlap_check_and_replaces_canonical_sentence():
    prompt = build_user_prompt(PROMPTS, EXISTING, mode="hardened")
    assert "0. Overlap check: compare the batch against EVERY existing category above." in prompt
    assert "Prefer the canonical name for a standard intent" not in prompt


def test_system_placement_moves_registry_to_system():
    system = build_system_prompt(existing=EXISTING, mode="system-placement", few_shot="none")
    user = build_user_prompt(PROMPTS, EXISTING, mode="system-placement")
    assert "Existing categories (name: description). Do not duplicate these concepts:" in system
    assert "- translation: Converting text between languages." in system
    assert "Existing categories" not in user


def test_cold_start_uses_none_yet():
    assert "(none yet)" in build_user_prompt(PROMPTS, None, mode="as-today")
    assert "(none yet)" in build_system_prompt(existing=None, mode="system-placement", few_shot="none")
