# Laya Router Ablations

## Design summary

The campaign uses paired permutation seeds (`13`, `42`, `77`) shared by every
cell. Factorial cells use no proposer few-shot context; anchor cells use the
full context. Runs use MLX, `aac6fef/laya-mlx`, and threshold `0.5` unless
overridden on the command line.

### Confidence gate policy

The default `bucket-topprob` gate uses the calibrated top probability rather
than normalized-entropy confidence: it demotes a non-`other` choice below
`0.5` when there are at most 10 probability entries, and below `0.9` when
there are 11 or more. The measured firing rates were 64%, 7%, and 0% at 5,
10, and 11 options respectively; at 11+ options the mean top probability was
`0.98+`. The explicit `frozen` policy preserves the historical strict
`confidence < 0.5` behavior. `anchor-cold-as-today` uses `frozen` as the
historical-fidelity / README anchor; every other cell uses `bucket-topprob`.

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
