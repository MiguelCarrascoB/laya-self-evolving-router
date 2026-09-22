#!/usr/bin/env python3
"""Run the paired Laya simulation ablation matrix."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


CELLS: tuple[dict[str, Any], ...] = (
    {"id": "cold-blind", "seed_file": None, "proposer": "blind", "few_shot": "none", "kind": "factorial", "dedup": None, "gate": "bucket-topprob"},
    {"id": "cold-as-today", "seed_file": None, "proposer": "as-today", "few_shot": "none", "kind": "factorial", "dedup": None, "gate": "bucket-topprob"},
    {"id": "cold-hardened", "seed_file": None, "proposer": "hardened", "few_shot": "none", "kind": "factorial", "dedup": None, "gate": "bucket-topprob"},
    {"id": "cold-system-placement", "seed_file": None, "proposer": "system-placement", "few_shot": "none", "kind": "factorial", "dedup": None, "gate": "bucket-topprob"},
    {"id": "seeded-blind", "seed_file": "data/seeds_canonical.json", "proposer": "blind", "few_shot": "none", "kind": "factorial", "dedup": None, "gate": "bucket-topprob"},
    {"id": "seeded-as-today", "seed_file": "data/seeds_canonical.json", "proposer": "as-today", "few_shot": "none", "kind": "factorial", "dedup": None, "gate": "bucket-topprob"},
    {"id": "seeded-hardened", "seed_file": "data/seeds_canonical.json", "proposer": "hardened", "few_shot": "none", "kind": "factorial", "dedup": None, "gate": "bucket-topprob"},
    {"id": "seeded-system-placement", "seed_file": "data/seeds_canonical.json", "proposer": "system-placement", "few_shot": "none", "kind": "factorial", "dedup": None, "gate": "bucket-topprob"},
    {"id": "anchor-cold-as-today", "seed_file": None, "proposer": "as-today", "few_shot": "full", "kind": "anchor", "dedup": None, "gate": "frozen"},
    {"id": "anchor-seeded-hardened", "seed_file": "data/seeds_canonical.json", "proposer": "hardened", "few_shot": "full", "kind": "anchor", "dedup": None, "gate": "bucket-topprob"},
    {"id": "stress-imperfect-hardened", "seed_file": "data/seeds_imperfect.json", "proposer": "hardened", "few_shot": "none", "kind": "stress", "dedup": None, "gate": "bucket-topprob"},
    {"id": "dedup-seeded-hardened", "seed_file": "data/seeds_canonical.json", "proposer": "hardened", "few_shot": "none", "kind": "dedup", "dedup": "token-jaccard-025", "enabled": True, "gate": "bucket-topprob"},
    {"id": "dedup-cold-hardened", "seed_file": None, "proposer": "hardened", "few_shot": "none", "kind": "dedup", "dedup": "token-jaccard-025", "enabled": True, "gate": "bucket-topprob"},
)
DEFAULT_SEEDS = (13, 42, 77)


def output_path(out_dir: str | Path, cell: dict[str, Any], permseed: int, repeat: int, repeats: int = 1) -> Path:
    name = f"{cell['id']}-fshot-{cell['few_shot']}-p{permseed}"
    if cell.get("dedup"):
        name += "-dedup-jaccard"
    if repeats > 1:
        name += f"-r{repeat}"
    return Path(out_dir) / f"{name}.json"


def selected_cells(only: str | None = None, kinds: str | None = None) -> list[dict[str, Any]]:
    wanted_ids = {item.strip() for item in only.split(",")} if only else None
    wanted_kinds = {item.strip() for item in kinds.split(",")} if kinds else None
    return [
        cell for cell in CELLS
        if cell.get("enabled", True)
        and (wanted_ids is None or cell["id"] in wanted_ids)
        and (wanted_kinds is None or cell["kind"] in wanted_kinds)
    ]


def build_command(cell: dict[str, Any], permseed: int, out: str | Path, backend: str, model: str, threshold: float) -> list[str]:
    command = [
        "uv", "run", "laya-router", "simulate",
        "--dataset", "data/dataset.jsonl", "--out", str(out),
        "--backend", backend, "--model", model, "--threshold", str(threshold), "--gate", cell.get("gate", "bucket-topprob"),
        "--seed", str(permseed),
    ]
    if cell.get("seed_file"):
        command += ["--seed-file", cell["seed_file"]]
    command += ["--proposer", cell["proposer"], "--few-shot", cell["few_shot"]]
    if cell.get("dedup"):
        command += ["--dedup", cell["dedup"]]
    return command


def valid_output(path: str | Path) -> bool:
    try:
        with Path(path).open(encoding="utf-8") as stream:
            json.load(stream)
        return True
    except (OSError, json.JSONDecodeError):
        return False


def _parse_seeds(value: str) -> list[int]:
    return [int(item.strip()) for item in value.split(",") if item.strip()]


def _print_matrix() -> None:
    print("id                         kind       seed_file                         proposer          few_shot  gate           dedup              enabled")
    print("-" * 126)
    for cell in CELLS:
        print(f"{cell['id']:<26} {cell['kind']:<10} {(cell.get('seed_file') or 'cold'):<34} {cell['proposer']:<17} {cell['few_shot']:<9} {cell.get('gate', 'bucket-topprob'):<14} {(cell.get('dedup') or 'none'):<18} {cell.get('enabled', True)}")


def _load_ledger(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true", dest="list_matrix", help="print the cell matrix and exit")
    parser.add_argument("--only", help="comma-separated cell ids to run")
    parser.add_argument("--kinds", help="comma-separated cell kinds to run (factorial, anchor, stress, dedup)")
    parser.add_argument("--seeds", default=",".join(map(str, DEFAULT_SEEDS)), help="comma-separated permutation seeds (default: %(default)s)")
    parser.add_argument("--repeat", type=int, default=1, help="repeats per cell/seed; >1 adds -rN filename suffixes")
    parser.add_argument("--out-dir", default="results/ablation", help="output directory (default: %(default)s)")
    parser.add_argument("--backend", default="mlx", help="Laya backend passed to simulate (default: %(default)s)")
    parser.add_argument("--model", default="aac6fef/laya-mlx", help="Laya model id (default: %(default)s)")
    parser.add_argument("--threshold", type=float, default=0.5, help="routing threshold (default: %(default)s)")
    parser.add_argument("--jobs", type=int, default=1, help="accepted for compatibility; runs are always sequential")
    parser.add_argument("--force", action="store_true", help="re-run even when a valid output JSON exists")
    parser.add_argument("--dry-run", action="store_true", help="print the commands without running them")
    args = parser.parse_args(argv)
    if args.repeat < 1 or args.jobs < 1:
        parser.error("--repeat and --jobs must be positive")
    try:
        seeds = _parse_seeds(args.seeds)
    except ValueError:
        parser.error(f"--seeds must be comma-separated integers, got {args.seeds!r}")
    if args.list_matrix:
        _print_matrix()
        return 0

    cells = selected_cells(args.only, args.kinds)
    jobs_note = " (sequential; MLX jobs are intentionally not parallelized)" if args.jobs > 1 else ""
    if args.jobs > 1:
        print(f"--jobs {args.jobs} requested; running sequentially{jobs_note}")
    runs: list[tuple[dict[str, Any], int, int, Path, list[str]]] = []
    for cell in cells:
        for seed in seeds:
            for repeat in range(1, args.repeat + 1):
                out = output_path(args.out_dir, cell, seed, repeat, args.repeat)
                command = build_command(cell, seed, out, args.backend, args.model, args.threshold)
                runs.append((cell, seed, repeat, out, command))
    if args.dry_run:
        for _, _, _, _, command in runs:
            print(" ".join(command))
        return 0

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ledger_path = out_dir / "ledger.json"
    ledger = _load_ledger(ledger_path)
    counts = {"planned": len(runs), "ok": 0, "failed": 0, "skipped": 0}
    summary: dict[str, list[str]] = {cell["id"]: [] for cell in cells}
    for cell, seed, repeat, out, command in runs:
        if str(out) not in summary[cell["id"]]:
            summary[cell["id"]].append(str(out))
        if not args.force and valid_output(out):
            print(f"SKIP {out} (valid JSON exists)")
            counts["skipped"] += 1
            ledger.append({"cell": cell["id"], "permseed": seed, "repeat": repeat, "out": str(out), "cmd": command, "exit_code": 0, "seconds": 0.0, "skipped": True})
            ledger_path.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
            continue
        started = time.monotonic()
        print("RUN " + " ".join(command))
        result = subprocess.run(command, check=False)
        seconds = round(time.monotonic() - started, 3)
        code = result.returncode
        counts["ok" if code == 0 else "failed"] += 1
        if code != 0:
            print(f"FAIL exit_code={code}: {' '.join(command)}", file=sys.stderr)
        ledger.append({"cell": cell["id"], "permseed": seed, "repeat": repeat, "out": str(out), "cmd": command, "exit_code": code, "seconds": seconds, "skipped": False})
        ledger_path.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")

    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"Summary: planned={counts['planned']} ok={counts['ok']} failed={counts['failed']} skipped={counts['skipped']}")
    return 0 if counts["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
