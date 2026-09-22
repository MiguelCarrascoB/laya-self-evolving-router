from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location("run_ablation", ROOT / "scripts/run_ablation.py")
assert SPEC and SPEC.loader
run_ablation = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(run_ablation)


def test_matrix_completeness_and_kinds():
    assert len(run_ablation.CELLS) == 13
    assert sum(c["kind"] == "factorial" for c in run_ablation.CELLS) == 8
    assert sum(c["kind"] == "anchor" for c in run_ablation.CELLS) == 2
    assert sum(c["kind"] == "stress" for c in run_ablation.CELLS) == 1
    assert sum(c["kind"] == "dedup" for c in run_ablation.CELLS) == 2
    assert all(c["few_shot"] == "none" for c in run_ablation.CELLS if c["kind"] in {"factorial", "stress", "dedup"})
    assert all(c["few_shot"] == "full" for c in run_ablation.CELLS if c["kind"] == "anchor")
    assert all(c.get("enabled", True) is False for c in run_ablation.CELLS if c["kind"] == "dedup")


def test_output_naming_including_repeats(tmp_path):
    cell = run_ablation.CELLS[0]
    assert run_ablation.output_path(tmp_path, cell, 13, 1) == tmp_path / "cold-blind-fshot-none-p13.json"
    assert run_ablation.output_path(tmp_path, cell, 13, 2, 2) == tmp_path / "cold-blind-fshot-none-p13-r2.json"


def test_filters():
    assert [c["id"] for c in run_ablation.selected_cells(only="cold-blind,anchor-cold-as-today")] == ["cold-blind", "anchor-cold-as-today"]
    assert all(c["kind"] == "factorial" for c in run_ablation.selected_cells(kinds="factorial"))
    assert not run_ablation.selected_cells(only="dedup-cold-hardened")


def test_command_construction():
    cell = next(c for c in run_ablation.CELLS if c["id"] == "seeded-hardened")
    assert run_ablation.build_command(cell, 42, "out.json", "mlx", "model", 0.5) == [
        "uv", "run", "laya-router", "simulate", "--dataset", "data/dataset.jsonl", "--out", "out.json",
        "--backend", "mlx", "--model", "model", "--threshold", "0.5", "--seed", "42",
        "--seed-file", "data/seeds_canonical.json", "--proposer", "hardened", "--few-shot", "none",
    ]


def test_skip_existing_logic(tmp_path):
    path = tmp_path / "result.json"
    path.write_text(json.dumps({"ok": True}), encoding="utf-8")
    assert run_ablation.valid_output(path)
    path.write_text("not json", encoding="utf-8")
    assert not run_ablation.valid_output(path)
