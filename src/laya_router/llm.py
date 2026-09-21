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

PROMPT_TEMPLATE = """You are designing categories for a prompt router.
Below are user prompts the router could not classify. Propose 1-2 broad, reusable
intent categories that cover them (a category can cover multiple prompts in the batch).
Rules:
- name: 1-3 words, lowercase, underscores.
- description: max 12 words explaining what belongs in it.
- NOT a near-duplicate of these existing categories: {existing}
- Categories must be intent kinds (like coding help, translation), not specific topics.
Return ONLY JSON: [{{\"name\": \"...\", \"description\": \"...\"}}]

Prompts:
{prompts}
"""


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

    def propose(self, prompts: list[str], existing: list[str], mask: str = "") -> list[ProposedCategory]:
        prompt = PROMPT_TEMPLATE.format(existing=", ".join(existing), prompts="\n".join(prompts))
        last_err: Exception | None = None
        client = self._client
        cfg = self._primary
        for attempt in (0, 1):
            try:
                try:
                    resp = client.chat.completions.create(
                        model=cfg["model"],
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.2,
                        max_tokens=400,
                    )
                except Exception as e:  # network/500 — try fallback client on second attempt
                    raise RuntimeError(f"primary failed: {e}") from e
                return self._parse(resp.choices[0].message.content or "")
            except Exception as e:  # noqa: BLE001
                last_err = e
                if self._fallback_client and attempt == 0:
                    client, cfg = self._fallback_client, self._fallback or cfg
                    continue
                break
        raise RuntimeError(f"category proposal failed: {last_err}")

    @staticmethod
    def _parse(text: str) -> list[ProposedCategory]:
        m = re.search(r"\[.*\]", text, re.S)
        if not m:
            raise ValueError(f"no JSON array in LLM response: {text[:120]!r}")
        out = []
        for item in json.loads(m.group(0)):
            name, desc = item.get("name", "").strip(), item.get("description", "").strip()
            if name and desc and len(desc.split()) <= 14:
                out.append(ProposedCategory(name=name, description=desc))
        return out

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
