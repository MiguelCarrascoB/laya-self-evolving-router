# Laya Router Ablations

## Design summary

The campaign uses paired permutation seeds (`13`, `42`, `77`) shared by every
cell. Factorial cells use no proposer few-shot context; anchor cells use the
full context. Runs use MLX, `aac6fef/laya-mlx`, and threshold `0.5` unless
overridden on the command line.

| Kind | Cells | Flags |
|---|---|---|
| factorial | `cold-*`, `seeded-*` (8) | `--few-shot none`; seeded cells use `data/seeds_canonical.json` |
| anchor | `anchor-cold-as-today`, `anchor-seeded-hardened` | `--few-shot full` |
| stress | `stress-imperfect-hardened` | `data/seeds_imperfect.json`, `--few-shot none` |
| dedup (disabled) | `dedup-seeded-hardened`, `dedup-cold-hardened` | `--few-shot none`; enable after the offline probe |

The comparison tracks `accuracy_final`, `dup_pairs`, `births_beyond_seeds`,
`novel_absorbed`, `label_match`, `coverage`, and `other_rate`, plus the
associated guardrails (run completion, registry cap, and malformed output
checks).

<!-- results table placeholder -->

## Reproduction

```bash
uv run python scripts/run_ablation.py --dry-run
```

Exact default dry-run commands:

```text
uv run laya-router simulate --dataset data/dataset.jsonl --out results/ablation/cold-blind-fshot-none-p13.json --backend mlx --model aac6fef/laya-mlx --threshold 0.5 --seed 13 --proposer blind --few-shot none
uv run laya-router simulate --dataset data/dataset.jsonl --out results/ablation/cold-blind-fshot-none-p42.json --backend mlx --model aac6fef/laya-mlx --threshold 0.5 --seed 42 --proposer blind --few-shot none
uv run laya-router simulate --dataset data/dataset.jsonl --out results/ablation/cold-blind-fshot-none-p77.json --backend mlx --model aac6fef/laya-mlx --threshold 0.5 --seed 77 --proposer blind --few-shot none
uv run laya-router simulate --dataset data/dataset.jsonl --out results/ablation/cold-as-today-fshot-none-p13.json --backend mlx --model aac6fef/laya-mlx --threshold 0.5 --seed 13 --proposer as-today --few-shot none
uv run laya-router simulate --dataset data/dataset.jsonl --out results/ablation/cold-as-today-fshot-none-p42.json --backend mlx --model aac6fef/laya-mlx --threshold 0.5 --seed 42 --proposer as-today --few-shot none
uv run laya-router simulate --dataset data/dataset.jsonl --out results/ablation/cold-as-today-fshot-none-p77.json --backend mlx --model aac6fef/laya-mlx --threshold 0.5 --seed 77 --proposer as-today --few-shot none
uv run laya-router simulate --dataset data/dataset.jsonl --out results/ablation/cold-hardened-fshot-none-p13.json --backend mlx --model aac6fef/laya-mlx --threshold 0.5 --seed 13 --proposer hardened --few-shot none
uv run laya-router simulate --dataset data/dataset.jsonl --out results/ablation/cold-hardened-fshot-none-p42.json --backend mlx --model aac6fef/laya-mlx --threshold 0.5 --seed 42 --proposer hardened --few-shot none
uv run laya-router simulate --dataset data/dataset.jsonl --out results/ablation/cold-hardened-fshot-none-p77.json --backend mlx --model aac6fef/laya-mlx --threshold 0.5 --seed 77 --proposer hardened --few-shot none
uv run laya-router simulate --dataset data/dataset.jsonl --out results/ablation/cold-system-placement-fshot-none-p13.json --backend mlx --model aac6fef/laya-mlx --threshold 0.5 --seed 13 --proposer system-placement --few-shot none
uv run laya-router simulate --dataset data/dataset.jsonl --out results/ablation/cold-system-placement-fshot-none-p42.json --backend mlx --model aac6fef/laya-mlx --threshold 0.5 --seed 42 --proposer system-placement --few-shot none
uv run laya-router simulate --dataset data/dataset.jsonl --out results/ablation/cold-system-placement-fshot-none-p77.json --backend mlx --model aac6fef/laya-mlx --threshold 0.5 --seed 77 --proposer system-placement --few-shot none
uv run laya-router simulate --dataset data/dataset.jsonl --out results/ablation/seeded-blind-fshot-none-p13.json --backend mlx --model aac6fef/laya-mlx --threshold 0.5 --seed 13 --seed-file data/seeds_canonical.json --proposer blind --few-shot none
uv run laya-router simulate --dataset data/dataset.jsonl --out results/ablation/seeded-blind-fshot-none-p42.json --backend mlx --model aac6fef/laya-mlx --threshold 0.5 --seed 42 --seed-file data/seeds_canonical.json --proposer blind --few-shot none
uv run laya-router simulate --dataset data/dataset.jsonl --out results/ablation/seeded-blind-fshot-none-p77.json --backend mlx --model aac6fef/laya-mlx --threshold 0.5 --seed 77 --seed-file data/seeds_canonical.json --proposer blind --few-shot none
uv run laya-router simulate --dataset data/dataset.jsonl --out results/ablation/seeded-as-today-fshot-none-p13.json --backend mlx --model aac6fef/laya-mlx --threshold 0.5 --seed 13 --seed-file data/seeds_canonical.json --proposer as-today --few-shot none
uv run laya-router simulate --dataset data/dataset.jsonl --out results/ablation/seeded-as-today-fshot-none-p42.json --backend mlx --model aac6fef/laya-mlx --threshold 0.5 --seed 42 --seed-file data/seeds_canonical.json --proposer as-today --few-shot none
uv run laya-router simulate --dataset data/dataset.jsonl --out results/ablation/seeded-as-today-fshot-none-p77.json --backend mlx --model aac6fef/laya-mlx --threshold 0.5 --seed 77 --seed-file data/seeds_canonical.json --proposer as-today --few-shot none
uv run laya-router simulate --dataset data/dataset.jsonl --out results/ablation/seeded-hardened-fshot-none-p13.json --backend mlx --model aac6fef/laya-mlx --threshold 0.5 --seed 13 --seed-file data/seeds_canonical.json --proposer hardened --few-shot none
uv run laya-router simulate --dataset data/dataset.jsonl --out results/ablation/seeded-hardened-fshot-none-p42.json --backend mlx --model aac6fef/laya-mlx --threshold 0.5 --seed 42 --seed-file data/seeds_canonical.json --proposer hardened --few-shot none
uv run laya-router simulate --dataset data/dataset.jsonl --out results/ablation/seeded-hardened-fshot-none-p77.json --backend mlx --model aac6fef/laya-mlx --threshold 0.5 --seed 77 --seed-file data/seeds_canonical.json --proposer hardened --few-shot none
uv run laya-router simulate --dataset data/dataset.jsonl --out results/ablation/seeded-system-placement-fshot-none-p13.json --backend mlx --model aac6fef/laya-mlx --threshold 0.5 --seed 13 --seed-file data/seeds_canonical.json --proposer system-placement --few-shot none
uv run laya-router simulate --dataset data/dataset.jsonl --out results/ablation/seeded-system-placement-fshot-none-p42.json --backend mlx --model aac6fef/laya-mlx --threshold 0.5 --seed 42 --seed-file data/seeds_canonical.json --proposer system-placement --few-shot none
uv run laya-router simulate --dataset data/dataset.jsonl --out results/ablation/seeded-system-placement-fshot-none-p77.json --backend mlx --model aac6fef/laya-mlx --threshold 0.5 --seed 77 --seed-file data/seeds_canonical.json --proposer system-placement --few-shot none
uv run laya-router simulate --dataset data/dataset.jsonl --out results/ablation/anchor-cold-as-today-fshot-full-p13.json --backend mlx --model aac6fef/laya-mlx --threshold 0.5 --seed 13 --proposer as-today --few-shot full
uv run laya-router simulate --dataset data/dataset.jsonl --out results/ablation/anchor-cold-as-today-fshot-full-p42.json --backend mlx --model aac6fef/laya-mlx --threshold 0.5 --seed 42 --proposer as-today --few-shot full
uv run laya-router simulate --dataset data/dataset.jsonl --out results/ablation/anchor-cold-as-today-fshot-full-p77.json --backend mlx --model aac6fef/laya-mlx --threshold 0.5 --seed 77 --proposer as-today --few-shot full
uv run laya-router simulate --dataset data/dataset.jsonl --out results/ablation/anchor-seeded-hardened-fshot-full-p13.json --backend mlx --model aac6fef/laya-mlx --threshold 0.5 --seed 13 --seed-file data/seeds_canonical.json --proposer hardened --few-shot full
uv run laya-router simulate --dataset data/dataset.jsonl --out results/ablation/anchor-seeded-hardened-fshot-full-p42.json --backend mlx --model aac6fef/laya-mlx --threshold 0.5 --seed 42 --seed-file data/seeds_canonical.json --proposer hardened --few-shot full
uv run laya-router simulate --dataset data/dataset.jsonl --out results/ablation/anchor-seeded-hardened-fshot-full-p77.json --backend mlx --model aac6fef/laya-mlx --threshold 0.5 --seed 77 --seed-file data/seeds_canonical.json --proposer hardened --few-shot full
uv run laya-router simulate --dataset data/dataset.jsonl --out results/ablation/stress-imperfect-hardened-fshot-none-p13.json --backend mlx --model aac6fef/laya-mlx --threshold 0.5 --seed 13 --seed-file data/seeds_imperfect.json --proposer hardened --few-shot none
uv run laya-router simulate --dataset data/dataset.jsonl --out results/ablation/stress-imperfect-hardened-fshot-none-p42.json --backend mlx --model aac6fef/laya-mlx --threshold 0.5 --seed 42 --seed-file data/seeds_imperfect.json --proposer hardened --few-shot none
uv run laya-router simulate --dataset data/dataset.jsonl --out results/ablation/stress-imperfect-hardened-fshot-none-p77.json --backend mlx --model aac6fef/laya-mlx --threshold 0.5 --seed 77 --seed-file data/seeds_imperfect.json --proposer hardened --few-shot none
```
