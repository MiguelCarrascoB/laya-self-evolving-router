"""Offline regression tests for script path-aliasing and CLI edge cases."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"scripts_{name}", ROOT / f"scripts/{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


semantic = _load("semantic_accuracy")
judge_registry = _load("judge_registry")
run_ablation = _load("run_ablation")
replay = _load("replay_precheck")


def _run(route: str, gt: str) -> dict:
    return {"events": [{"id": "a", "route": route, "ground_truth": gt}]}


def test_semantic_lookup_matches_relative_absolute_and_name(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    mappings = {"results/ablation/x-fshot-none-p1.json": {"c": "coding_help"}}
    assert semantic.lookup_mapping(mappings, "results/ablation/x-fshot-none-p1.json") == {"c": "coding_help"}
    assert semantic.lookup_mapping(mappings, str(tmp_path / "results/ablation/x-fshot-none-p1.json")) == {"c": "coding_help"}
    assert semantic.lookup_mapping(mappings, "/elsewhere/x-fshot-none-p1.json") == {"c": "coding_help"}
    assert semantic.lookup_mapping(mappings, "results/ablation/missing.json") == {}
    # An ambiguous basename must not guess.
    two = {"a/x.json": {"c": "shopping"}, "b/x.json": {"c": "translation"}}
    assert semantic.lookup_mapping(two, "/other/x.json") == {}


def test_semantic_main_scores_absolute_ablation_dir(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    ablation = tmp_path / "results/ablation"
    ablation.mkdir(parents=True)
    (ablation / "cold-blind-fshot-none-p1.json").write_text(json.dumps(_run("c", "coding_help")))
    judge = {"run_config": {}, "results/ablation/cold-blind-fshot-none-p1.json":
             {"mapping": [{"name": "c", "mapped_to": "coding_help"}]}}
    (ablation / "judge.json").write_text(json.dumps(judge))
    semantic.main(["--judge", str(ablation / "judge.json"), "--ablation-dir", str(ablation)])
    assert "cold-blind  1.000±0.000  1.000  1.000  (n=1)" in capsys.readouterr().out


def test_judge_resume_matches_prior_key_by_resolved_path(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(judge_registry, "load_dotenv", lambda *a, **k: False)

    def no_network(*_args, **_kwargs):
        raise AssertionError("resume should not re-judge")

    monkeypatch.setattr(judge_registry, "_judge", no_network)
    run = tmp_path / "run.json"
    run.write_text(json.dumps({"registry_final": {"categories": ["a"]}}))
    summary = judge_registry._summary(1, [{"name": "a", "mapped_to": "shopping"}], [])
    prior = {"run_config": {}, "run.json": {"mapping": [], "dup_pairs": [], "fragmentation": {},
                                            "summary": summary, "warnings": [], "judged_ok": True}}
    out = tmp_path / "judge.json"
    out.write_text(json.dumps(prior))
    assert judge_registry.main([str(run), "--out", str(out)]) == 0
    saved = json.loads(out.read_text())
    assert set(saved) == {"run_config", "run.json"}


def test_judge_skips_missing_file(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(judge_registry, "load_dotenv", lambda *a, **k: False)
    out = tmp_path / "judge.json"
    assert judge_registry.main([str(tmp_path / "missing.json"), "--out", str(out)]) == 0
    assert "unreadable" in capsys.readouterr().err


def test_run_ablation_rejects_bad_seeds(capsys):
    with pytest.raises(SystemExit) as exc:
        run_ablation.main(["--seeds", "1,x", "--dry-run"])
    assert exc.value.code == 2
    assert "--seeds must be comma-separated integers" in capsys.readouterr().err


def test_replay_main_tolerates_modes_with_zero_calls(tmp_path, monkeypatch, capsys):
    source = tmp_path / "in.json"
    source.write_text("{}")
    report = {"modes": {m: {"proposals": 0, "empty": 0, "has_similar_rejected": 0,
                            "overlap_flagged": 0, "parse_failures": 0} for m in replay.MODES},
              "call_records": [], "dedup_variants": {}}
    monkeypatch.setattr(replay, "load_providers", lambda: None)
    monkeypatch.setattr(replay, "run_replay", lambda *a, **k: report)
    monkeypatch.setattr("sys.argv", ["replay_precheck.py", "--input", str(source),
                                     "--out", str(tmp_path / "out.json"), "--max-calls", "0"])
    replay.main()
    assert "| blind | 0 | n/a |" in capsys.readouterr().out
