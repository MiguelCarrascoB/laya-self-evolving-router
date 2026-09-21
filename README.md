# laya-self-evolving-router (PoC)

**Self-evolving prompt-intent router**: [Laya](https://github.com/NandhaKishorM/laya) typed decisions (via [laya-mlx](https://github.com/mizorewww/laya-mlx) / [laya-coreml](https://github.com/mizorewww/laya-coreml)) classify incoming prompts in **~10–20 ms locally with zero generated tokens**. Prompts that don't fit (or score below a confidence threshold) land in `other`; those prompts are batched and an LLM proposes **new reusable intent categories** that Laya can immediately use. Starting category set: **zero**.

## How it works

```
prompt ──► laya.choice(categories ∪ {other}) ──► confident hit  → routed
                                              └─► "other" / low confidence
                                                     │ batch every N
                                                     ▼
                                            LLM proposes ≤2 categories
                                                     │
                                            laya registry grows → re-route pending
```

Key details:
- **Choice options are built per call** from the living category registry (`categories.py`), name + one-line description each, capped at 30 (512-token Laya context).
- **Confidence gate**: top non-`other` option under `--threshold` (default 0.5) is also treated as `other`.
- LLM calls are minimal: one batched call per 10 accumulated `other` prompts, return-only-JSON constraint (`llm.py`).
- Every routing decision, probability, latency, category birth and re-route is logged to `results/results.json` (`simulation.py`).

## Layout

```
src/laya_router/    router, categories, LLM provider (OpenAI-compatible + LMStudio fallback), simulation, CLI
data/dataset.jsonl  650 synthetic prompts: 10 seeded intents (55×) + 100 deliberately novel (10×)
visualizer/visualizer.html  single-file, offline dashboard (timeline scrubber, charts, event log)
results/            simulation output (JSON) — power the visualizer
```

## Run it

```bash
uv sync
cp .env.example .env          # put OPENAI_API_KEY in .env (gitignored)
uv run laya-router simulate   # closed-loop over data/dataset.jsonl
uv run laya-router live       # type prompts, watch categories appear

# open the visualizer
cd . && python -m http.server 8787 --directory results
# visit http://localhost:8787/../visualizer/visualizer.html or open the html directly
```

Core ML comparison (Python ≤3.13 env):

```bash
uv sync --extra coreml                       # or a python 3.13 venv: laya-coreml requires <3.14
uv run laya-router simulate --backend coreml --model aac6fef/laya-coreml --out results/results-coreml.json
```

## Results (M4 Pro, 650 prompts)

Run 1 — `aac6fef/laya-mlx` FP16 (`results/results.json`), LLM category discovery via an OpenAI-compatible model:

| Metric | MLX | CoreML (`aac6fef/laya-coreml`) |
|---|---:|---:|
| Coverage (routed out of `other`) | **67.4%** | 63.2% |
| Other-rate at end | 32.6% | 36.8% |
| Seed categories recovered by name | 5/10 | 2/10 |
| Discovered novel categories | watch_basics, plant_care, genealogy_research, astronomy_concepts, travel_*, wine... | vehicle_maintenance, genealogy_research, houseplant_care, wine_tasting, sports_betting... |
| Decision latency p50 | **27.4 ms** | 28.3 ms |
| Decision latency p95 | **32.7 ms** | 365 ms (first-calls Core ML init) |
| LLM calls for 100 novel prompts | ~30 batched calls | ~30 batched calls |

What this shows:
- **Cold start works**: 0 categories → `other` → batches of LLM proposals → Laya routes with the grown registry within the first ~15% of the stream.
- **Taxonomy is the bottleneck, not Laya**: the discovered categories are valid intents but rarely collide with a fixed evaluation taxonomy — exact-label match is the wrong headline; coverage + seed recovery is the honest view.
- Core ML ≈ same accuracy, similar p50, higher tail from Core ML pipeline initialization on first long inputs.

## License

Apache-2.0, like laya-mlx/laya-coreml.
