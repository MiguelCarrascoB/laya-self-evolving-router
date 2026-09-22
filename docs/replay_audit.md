# Manual semantic audit — replay pre-test proposals

Method: hand-read of all 85 proposals from `results/replay/precheck.json` (36 proposer
calls: 4 prompt modes × 3 frozen registry snapshots × 3 held-prompt batches), judged
against each snapshot's existing categories and against the other proposals of the same
mode. This is the manual leg of the Q3/Q14 metric policy; the machine legs are the
`dup_pairs` judge and the lexical dedup rules.

## Findings

**F1 — Cross-batch synonymy is the dominant duplication channel, and lexical rules miss
it.** With a frozen *empty* snapshot (k=0), each mode re-coined the same top intents under
fresh names across the three batches — a live preview of what the closed loop does before
those categories exist:

| Mode | Writing-intent names coined across 3 batches |
|---|---|
| blind | `professional_writing`, `text_rewriting`, `writing_revision` |
| as-today | `document_writing`, `writing_editing`, `writing_revision` |
| hardened | `professional_writing`, `content_writing`, `writing_revision` |
| system-placement | `professional_writing`, `content_adaptation`, `writing_revision` |

These are true same-scope duplicates (verified by description) with no shared salient
tokens (`rewriting` ≠ `writing` in the tokenizer), so Jaccard@0.25 does not flag them.
This is exactly the `translation` + `language_interpretation` + `language_learning`
pattern found in the historical v3-full registry.

**F2 — Duplicates-of-existing that BOTH lexical proxies miss.** Against the k=10 snapshot
(which contains `writing_editing`, `scheduling`, `fitness_health`, …), `blind` proposed:

- `professional_writing` — true dup of existing `writing_editing` (both: draft/revise
  written text); neither `has_similar` nor token-overlap flags it.
- `calendar_management` — borderline-true dup of existing `scheduling` (reminders and
  appointment scheduling are in `scheduling`'s stated scope).
- `health_guidance` — borderline overlap with existing `fitness_health` (physical-health
  questions); defensible as a sub-intent split.

→ Lexical rules cannot be the duplication guarantee; the semantic `dup_pairs` judge is a
required primary metric, as the registry audit predicted.

**F3 — What the lexical catches are worth.** High precision, partial recall: `has_similar`
catches the containment class (`plant_care`/`houseplant_care`), `token_jaccard_025` adds
the shared-token class (`travel_planning`/`travel_logistics`) — their union was 4/4 on the
probe's proxy flags. `embedding_cosine_085` caught nothing; the 0.85 threshold is likely
too tight for 15-word texts (follow-up: sweep 0.70–0.85 before discarding embeddings).

**F4 — Mode effect (the B mechanism), semantically read.** `blind` repeatedly proposes
intents the snapshot already covers; `hardened` and `system-placement` convert those cases
into `[]` (11% / 22% empty rates vs 0%). `system-placement` is the most conservative — the
campaign must watch whether that caution costs discovery (births-beyond-seeds,
novel-absorption). Suggestive-only: the registry-feedback modes converged on conventional
names (`data_analysis`, `meal_planning`) at `few_shot=none` where `blind` drifted
(`statistical_analysis`, `schedule_availability`); n is too small for a claim.

**F5 — Caveats.** Proposer sampling is uncontrolled (provider rejects `temperature=0`).
Frozen snapshots overstate k=0 cross-batch collisions relative to the real loop (where
earlier batches populate `existing`) — but F1's zero-token synonymy survives `existing`
checks regardless, as the historical registries confirm.

## Verdict

Campaign metrics stand as designed: `dup_pairs` (judge) primary, `fragmentation` for the
splitting channel, lexical union rule as the dedup-cell variant. Expected result shape:
strict synonym pairs are rare in final registries but borderline overlap + fragmentation
carry the signal — B should move both, and the judge is the only leg that can see F1/F2
class duplicates at all.
