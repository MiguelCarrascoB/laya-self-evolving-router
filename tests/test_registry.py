"""Pure unit tests for the category registry."""

from laya_router.categories import CategoryRegistry


def test_near_duplicate_and_substring_semantics():
    registry = CategoryRegistry()
    assert registry.add("plant_care", "Plants", 1, ["p1"])
    assert registry.add("houseplant_care", "Houseplants", 2, ["p2"]) is None
    assert registry.rejections[-1]["reason"] == "duplicate"

    for name in ("math_homework", "math_help", "cooking_recipes", "cooking_tips", "shopping", "gift_ideas"):
        assert registry.add(name, name, 3, []) is not None


def test_seeded_categories_and_rejections():
    registry = CategoryRegistry()
    cat = registry.seed("plant_care", "Plants")
    assert cat is not None
    assert cat.seeded is True
    assert cat.created_at_step == 0

    assert registry.seed("houseplant_care", "Houseplants", source_ids=("s1",)) is None
    assert registry.seed_rejections == [
        {"name": "houseplant_care", "reason": "duplicate", "step": 0, "source_ids": ["s1"]}
    ]
    assert registry.add("houseplant_care", "Houseplants", 4, ["p4"]) is None
    assert registry.rejections[-1]["reason"] == "duplicate"


def test_seed_and_add_fill_cap():
    registry = CategoryRegistry()
    for i in range(10):
        assert registry.seed(f"seed_{i}", "seed") is not None
    for i in range(20):
        assert registry.add(f"discovery_{i:02d}_category", "discovery", i + 1, []) is not None
    assert len(registry.all()) == 30
    assert registry.is_full()
    assert registry.add("last", "last", 99, ["p99"]) is None
    assert registry.rejections[-1] == {
        "name": "last",
        "reason": "cap",
        "step": 99,
        "source_ids": ["p99"],
    }


def test_as_dicts_and_growth_history_include_seeds():
    registry = CategoryRegistry()
    registry.seed("seed", "Seed description")
    registry.add("discovery", "Discovery description", 7, ["p7"])

    assert registry.as_dicts() == [
        {
            "name": "seed",
            "description": "Seed description",
            "created_at_step": 0,
            "created_from": [],
            "seeded": True,
        },
        {
            "name": "discovery",
            "description": "Discovery description",
            "created_at_step": 7,
            "created_from": ["p7"],
            "seeded": False,
        },
    ]
    assert registry.growth_history() == [
        {"step": 0, "name": "seed", "from": []},
        {"step": 7, "name": "discovery", "from": ["p7"]},
    ]


def test_add_rejection_records_all_fields():
    registry = CategoryRegistry()
    registry.add("plant_care", "Plants", 1, ["p1"])
    assert registry.add("houseplant_care", "Houseplants", 8, ["p8", "p9"]) is None
    assert registry.rejections == [
        {
            "name": "houseplant_care",
            "reason": "duplicate",
            "step": 8,
            "source_ids": ["p8", "p9"],
        }
    ]
