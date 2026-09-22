"""Argparse defaults and wiring for the CLI (no model / Laya load)."""

import json

import pytest

from laya_router.cli import _load_seed_categories, _resolve_dedup, _resolve_few_shot, build_parser


def test_simulate_defaults():
    args = build_parser().parse_args(["simulate"])
    assert args.cmd == "simulate"
    assert args.dataset == "data/dataset.jsonl"
    assert args.out == "results/results.json"
    assert args.backend == "mlx"
    assert args.model is None
    assert args.threshold == 0.5
    assert args.gate == "bucket-topprob"
    assert args.seed is None
    assert args.seed_file is None
    assert args.proposer == "as-today"
    assert args.few_shot is None
    assert args.dedup == "none"


def test_simulate_flags():
    args = build_parser().parse_args([
        "simulate",
        "--seed", "42",
        "--seed-file", "seeds.json",
        "--proposer", "hardened",
        "--few-shot", "three",
        "--threshold", "0.6",
        "--gate", "frozen",
    ])
    assert args.seed == 42
    assert args.seed_file == "seeds.json"
    assert args.proposer == "hardened"
    assert args.few_shot == "three"
    assert args.threshold == 0.6
    assert args.gate == "frozen"


def test_proposer_choices_reject_invalid():
    with pytest.raises(SystemExit):
        build_parser().parse_args(["simulate", "--proposer", "bogus"])


def test_dedup_flag_maps_to_registry_setting():
    assert _resolve_dedup("none") is None
    assert _resolve_dedup("token-jaccard-025") == "token_jaccard_025"
    assert build_parser().parse_args(["live", "--dedup", "token-jaccard-025"]).dedup == "token-jaccard-025"


def test_few_shot_choices_reject_invalid():
    with pytest.raises(SystemExit):
        build_parser().parse_args(["simulate", "--few-shot", "bogus"])


def test_live_mirrors_proposer_flags():
    args = build_parser().parse_args([
        "live", "--proposer", "system-placement", "--few-shot", "none", "--seed-file", "s.json",
    ])
    assert args.proposer == "system-placement"
    assert args.few_shot == "none"
    assert args.seed_file == "s.json"
    assert args.gate == "bucket-topprob"


def test_resolve_few_shot_default_full(monkeypatch):
    monkeypatch.delenv("LAYASYS_FEWSHOT", raising=False)
    assert _resolve_few_shot(None) == "full"
    assert _resolve_few_shot("none") == "none"


def test_resolve_few_shot_env(monkeypatch):
    monkeypatch.setenv("LAYASYS_FEWSHOT", "three")
    assert _resolve_few_shot(None) == "three"
    assert _resolve_few_shot("full") == "full"


def test_load_seed_categories(tmp_path):
    p = tmp_path / "seeds.json"
    p.write_text(json.dumps([
        {"name": "a", "description": "A"},
        {"name": "b", "description": "B"},
    ]))
    assert _load_seed_categories(str(p)) == [
        {"name": "a", "description": "A"},
        {"name": "b", "description": "B"},
    ]
    assert _load_seed_categories(None) is None


def test_load_seed_categories_rejects_non_list(tmp_path):
    p = tmp_path / "seeds.json"
    p.write_text(json.dumps({"name": "a"}))
    with pytest.raises(ValueError):
        _load_seed_categories(str(p))


def test_load_seed_categories_rejects_missing_fields(tmp_path):
    p = tmp_path / "seeds.json"
    p.write_text(json.dumps([{"name": "a"}]))
    with pytest.raises(ValueError):
        _load_seed_categories(str(p))
