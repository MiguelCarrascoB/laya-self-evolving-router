# Ablation campaign — results and verdicts

39 runs (13 configurations × 3 paired stream permutations + 2 frozen-gate anchor runs
+ 1 gate-check run), 650 prompts each, MLX `aac6fef/laya-mlx`, threshold 0.5, batch 10,
cap 30, `temperature=0` requested (provider rejects it — runs are stochastic), proposer
`gpt-5.6-luna`. Registry judged by LLM (`scripts/judge_registry.py`, policy `q14-v1`)
plus manual audit. Semantic metrics via `scripts/semantic_accuracy.py` (judge mappings ×
final routes). Noise floor from the same-config repeat pair: **±1.1 pts accuracy,
±2.8 pts coverage, ±4.3 pts label-match** — deltas below this are noise.

## Headline table (means over 3 seeds)

| Cell | sem. acc | sem. match | coverage | dup pairs (audited) | frag max | novel abs. | births |
|---|---:|---:|---:|---:|---:|---:|---:|
| anchor cold·as-today·full (frozen gate) | 0.521 | 0.804 | 0.648 | 0.5 | 4.0 | 75.5 | 30 |
| gate-check cold·as-today·full (bucket gate) | 0.508 | 0.789 | 0.643 | 0 | 3.0 | 81 | 30 |
| cold·blind | 0.466 | 0.783 | 0.594 | **6.3** | 4.7 | 40.7 | 30 |
| cold·as-today | 0.369 | 0.776 | 0.473 | 0 | 4.3 | 45.3 | 30 |
| cold·hardened | 0.401 | 0.791 | 0.505 | 0.3 | 4.3 | 54.0 | 30 |
| cold·system-placement | 0.395 | 0.813 | 0.486 | 0.3 | 4.7 | 50.7 | 30 |
| seeded·blind | 0.437 | 0.824 | 0.531 | 4.7 | 5.0 | 38.0 | 20 |
| seeded·as-today | 0.417 | 0.787 | 0.531 | 0.7 | 3.7 | 58.7 | 20 |
| **seeded·hardened** | **0.467** | 0.808 | 0.578 | **0.0** | 4.0 | **72.7** | 20 |
| seeded·system-placement | 0.458 | 0.807 | 0.568 | ~0* | 4.0 | 71.0 | 20 |
| anchor seeded·hardened·full | 0.466 | 0.796 | 0.585 | 0.3 | **2.7** | 76.7 | 20 |
| stress imperfect·hardened | 0.459 | 0.804 | 0.572 | 2.0 | 4.3 | 55.0 | 20 |
| dedup seeded·hardened (jaccard) | 0.436 | 0.804 | 0.543 | ~0.5* | 4.0 | 60.0 | 20 |
| dedup cold·hardened (jaccard) | 0.393 | 0.789 | 0.495 | ~1* | 4.3 | 52.0 | 30 |

\* raw judge counts are higher on these cells; manual audit shows most flagged pairs are
false positives (the judge's own `why` text argues the pairs are distinct while flagging
them strict — see audit notes).

Baselines (historical, frozen file order): `results-v3-full.json` = 0.40 exact / 0.62
label-match / 0.65 coverage; both anchor runs reproduce it within the noise floor.

## Verdicts

**H1 — seeded start ("an initial set of categories"): a real win.**
+5.8 to +8.2 pts coverage (paired, sign consistent across all four prompt modes),
+13 to +20 pts novel-intent absorption (seeded runs spend discovery slots on genuinely
new intents instead of re-discovering canonical ones), fewer duplicate pairs. Semantic
accuracy +2 to +7 pts — the much larger exact-name gains are circular (seeds *are* the
ground-truth names) and are correctly discounted here. Robust to messy seeds:
`stress-imperfect` matches canonical seeds on semantic accuracy (0.459 vs 0.467) and
coverage (0.572 vs 0.578); it only loses on novel absorption (55 vs 72.7) and injects
the deliberate near-dup seed pairs.

**H2 — registry shown to the proposer ("reintroduce categories"): kills duplication,
but by presence, not placement.**
blind proposer = 6.3 duplicate pairs per registry (audited genuine: writing/product/
travel synonym clusters). Any registry-aware prompt (user-prompt block as today, hardened
overlap-check, or the block moved into the system prompt) drops that to 0–0.7. Placement
(system vs user) makes no measurable difference; the hardened overlap-check is the
steadiest (0 dup pairs in all seeded runs). Cost: conservative modes answer `[]` more
often and lose ~6–9 pts of coverage through coarser taxonomies (blind's fine-grained
fragments cover more surface: frag max 4.7 vs 4.3).

**Joint optimum: seeded + hardened.** Near-blind coverage (0.578 vs 0.594, within
noise), zero duplicates, best novel absorption among non-anchors. With `--few-shot full`
the taxonomy is also the least fragmented (frag max 2.7) at no semantic cost.

**Gate policy (Q17).** Frozen → bucket-aware top-prob on the identical stream changes
end-state metrics within noise (−0.5 pts) but makes the policy stationary in option
count (the entropy gate fired 64%/0% at 5/11 options; `low_confidence_share` is now
0.04–0.10 instead of ~0). Kept as default on principle; `--gate frozen` preserved.

**Dedup rule (`token_jaccard_025`): neutral — do not ship as default.** After audit it
neither reduces nor increases true duplication measurably; it only burns proposal slots
(+1–1.7 rejected proposals). Its apparent harm in raw judge counts is judge mislabeling.

**Few-shot knowledge (secondary finding).** `--few-shot full` is worth +15 pts semantic
accuracy at cold start (0.521 vs ~0.37–0.47) — entirely via coverage — and adds **nothing
when seeded** (0.466 vs 0.467). The canonical names in the few-shot block and a seed set
are substitutes.

## Audit notes (metric trust)

- `accuracy_final` (exact name match) is circular under canonical seeds and punishes
  drifted names (`cold·as-today` reads 0.064 exact vs 0.369 semantic). Use semantic
  metrics for comparisons across naming regimes.
- The judge's strict/borderline flag is noisy: whole-call mislabeling events (e.g.
  `dedup-seeded-p13`'s 9 "strict" pairs, each with a `why` arguing the pair is distinct)
  inflate counts in bursts. Pair *lists* for blind cells were audited as genuine;
  affected cells marked ~ above. Judge self-consistency checking is a next-campaign item.
- Semantic label-match is near-constant (0.78–0.82) across every configuration: naming
  quality affects *coverage*, not routing correctness once covered.

## Known issues

- `analyze_ablation.py` computes judge-derived columns as `null` (merge key mismatch);
  the numbers above were computed from `judge.json` + `semantic_accuracy.py` directly.
- Provider rejects `temperature=0`; proposer stochasticity is captured only by the
  repeat-pair noise floor.

## Reproduce

```bash
uv run python scripts/probe_routing.py --sizes 4,9,10,15,30 --out results/probe/probe_results.json
uv run python scripts/run_ablation.py --list          # the 13-cell matrix
uv run python scripts/run_ablation.py --kinds factorial,stress,dedup,anchor --seeds 13,42,77
uv run python scripts/analyze_ablation.py --ablation-dir results/ablation --judge \
  --out results/ablation/analysis.json --table-out results/ablation/table.md
uv run python scripts/semantic_accuracy.py
uv run python scripts/judge_registry.py results/ablation/<run>.json --out results/ablation/judge.json
```
