"""OpenAI-compatible LLM client with LMStudio fallback and secure defaults.

The API key is read from the environment (OPENAI_API_KEY) or a gitignored
.env file — never from code, never logged.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    def load_dotenv(*_a, **_k):  # type: ignore[misc]
        return False


@dataclass
class ProposedCategory:
    name: str
    description: str


# Canonical intent names with clean, discriminating descriptions. The router
# recovers standard intents exactly when the proposer reuses these verbatim.
FEWSHOT_EXAMPLES: list[tuple[str, str]] = [
    ("coding_help", "Debugging, refactoring, or explaining programming problems."),
    ("translation", "Converting text between languages or adjusting its register."),
    ("data_analysis", "Summarizing, comparing, or finding patterns in data."),
    ("scheduling", "Planning, reminding, or distributing tasks across time."),
    ("shopping", "Choosing, comparing, or buying products and gifts."),
    ("math_homework", "Solving or explaining math problems and exercises."),
    ("cooking_recipes", "Recipes, ingredients, and meal preparation."),
    ("fitness_health", "Exercise, workouts, and physical-health questions."),
    ("travel_planning", "Planning trips, destinations, and itineraries."),
    ("writing_editing", "Improving, rewriting, or polishing written text."),
]

SYSTEM_PROMPT_TEMPLATE = """You are the taxonomy designer for a production prompt router.
The router classifies user prompts into intent categories; prompts that fit no
existing category fall into a holding "other" bucket. Your job is to propose NEW
categories so the router can absorb those prompts.

Use these canonical names verbatim whenever a batch clearly matches that intent
(do not coin synonyms):
{examples}

Avoid catch-all or vague names such as "general_help", "information",
"recommendations", "assistance", "requests", "misc", or "other". Avoid names so
narrow they describe a single prompt (e.g. "web_layout_centering_fix") rather
than a reusable intent.

Rules for every proposed category:
- name: 1-3 words, lowercase, underscores, one distinct concrete intent.
- description: at most 12 words stating what belongs in the category."""

SYSTEM_PROMPT_NO_FEWSHOT = """You are the taxonomy designer for a production prompt router.
The router classifies user prompts into intent categories; prompts that fit no
existing category fall into a holding "other" bucket. Your job is to propose NEW
categories so the router can absorb those prompts.

Avoid catch-all or vague names such as "general_help", "information",
"recommendations", "assistance", "requests", "misc", or "other". Avoid names so
narrow they describe a single prompt rather than a reusable intent.

Rules for every proposed category:
- name: 1-3 words, lowercase, underscores, one distinct concrete intent.
- description: at most 12 words stating what belongs in the category."""

PROMPT_TEMPLATE = """Existing categories (name: description). Do not duplicate these concepts:
{existing}

Unclassified prompts (one per line):
{prompts}

Propose up to 3 new, DISTINCT intent categories covering the biggest coherent
groups of prompts that no existing category above already covers. Prefer the
canonical name for a standard intent; if a canonical intent is too broad or
diverse in this batch, propose narrower, specific categories instead so the
router can match them confidently. If nothing new is needed, return [].

Proposal rules:
- name: 1-3 words, lowercase, underscores, a distinct concrete intent.
- description: at most 12 words stating what belongs in the category.
- No catch-alls ("general_help", "recommendations", "information", "requests").
- Do not near-duplicate the concept of any existing category above.

Return ONLY a JSON array, for example:
[{{"name": "translation", "description": "Converting text between languages."}}]"""


def _build_system_prompt() -> str:
    """Selects the system prompt by the LAYASYS_FEWSHOT env var.

    Values: "full" (default, all canonical examples), "three" (first 3 only),
    or "none" (role + rules, no examples).
    """
    mode = os.getenv("LAYASYS_FEWSHOT", "full").strip().lower()
    if mode == "none":
        return SYSTEM_PROMPT_NO_FEWSHOT
    n = 3 if mode in ("three", "3") else len(FEWSHOT_EXAMPLES)
    examples = "\n".join(f'- "{name}" — {desc}' for name, desc in FEWSHOT_EXAMPLES[:n])
    return SYSTEM_PROMPT_TEMPLATE.format(examples=examples)


class LLMCategoryProposer:
    def __init__(self, primary_cfg: dict, fallback_cfg: dict | None) -> None:
        from openai import OpenAI

        self._client = OpenAI(
            base_url=primary_cfg["base_url"],
            api_key=primary_cfg.get("api_key", ""),
        )
        self._primary = primary_cfg
        self._fallback = fallback_cfg
        self._fallback_client = None
        if fallback_cfg:
            self._fallback_client = OpenAI(
                base_url=fallback_cfg["base_url"],
                api_key=fallback_cfg.get("api_key", "lm-studio"),
            )

    def propose(
        self,
        prompts: list[str],
        existing: list[dict],
        system_prompt: str | None = None,
    ) -> list[ProposedCategory]:
        """Proposes 0-2 new categories for prompts the router can't classify.

        `existing` is a list of dicts with "name" and "description" keys, so the
        model can avoid proposing near-duplicates of what already exists.
        """
        if system_prompt is None:
            system_prompt = _build_system_prompt()

        existing_lines = [
            f'- {c["name"]}: {c["description"]}' for c in existing if c.get("name")
        ]
        existing_text = "\n".join(existing_lines) if existing_lines else "(none yet)"
        prompt = PROMPT_TEMPLATE.format(
            existing=existing_text, prompts="\n".join(prompts)
        )
        messages = [{"role": "system", "content": system_prompt}]
        messages.append({"role": "user", "content": prompt})

        # (client, cfg, label) chain: primary → primary retry → fallback → primary
        attempts = [("primary", self._client, self._primary)] * 2
        if self._fallback_client:
            attempts.append(("fallback", self._fallback_client, self._fallback))
            attempts.append(("primary", self._client, self._primary))

        last_err: Exception | None = None
        for label, client, cfg in attempts:
            import sys
            try:
                resp = client.chat.completions.create(
                    model=cfg["model"],
                    messages=messages,
                    max_completion_tokens=1200,
                )
                out = self._parse(resp.choices[0].message.content or "")
                if label != "primary":
                    print(f"[llm] primary failed; recovered via {label}", file=sys.stderr)
                return out
            except Exception as e:  # noqa: BLE001
                last_err = e
                print(f"[llm] {label} attempt failed: {e}", file=sys.stderr)
        raise RuntimeError(f"category proposal failed after all attempts: {last_err}")

    @staticmethod
    def _from_obj(obj) -> list[ProposedCategory]:
        if not isinstance(obj, list):
            return []
        out = []
        for item in obj:
            if not isinstance(item, dict):
                continue
            name, desc = item.get("name", "").strip(), item.get("description", "").strip()
            if name and desc and len(desc.split()) <= 14:
                out.append(ProposedCategory(name=name, description=desc))
        return out

    @staticmethod
    def _parse(text: str) -> list[ProposedCategory]:
        text = text.strip()
        # Direct JSON (whole payload).
        try:
            return LLMCategoryProposer._from_obj(json.loads(text))
        except Exception:
            pass
        # Simple bracketed arrays (descriptions have no nesting).
        for cand in re.findall(r"\[[^\[\]]*\]", text):
            try:
                parsed = LLMCategoryProposer._from_obj(json.loads(cand))
                if parsed:
                    return parsed
            except Exception:
                continue
        # Last-resort greedy block.
        m = re.search(r"\[.*\]", text, re.S)
        if m:
            try:
                return LLMCategoryProposer._from_obj(json.loads(m.group(0)))
            except Exception:
                pass
        raise ValueError(f"no JSON array in LLM response: {text[:120]!r}")

    @property
    def batch_size(self) -> int:
        return 10  # max prompts per proposal call


def load_providers() -> LLMCategoryProposer:
    """Loads config from env/.env; raises a clear error when no key is set."""
    load_dotenv()
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    api_key = os.getenv("OPENAI_API_KEY", "")
    model = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")
    primary = {"base_url": base_url, "model": model, **({"api_key": api_key} if api_key else {})}
    lm_url = os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234/v1")
    lm_model = os.getenv("LMSTUDIO_MODEL", "qwen2.5-7b-instruct")
    fallback = {"base_url": lm_url, "model": lm_model}
    return LLMCategoryProposer(primary, fallback)
