"""Router core: Laya + evolving category registry, per-step event log."""

from __future__ import annotations

import time

from .categories import CategoryRegistry
from .llm import LLMCategoryProposer

OTHER = "other"
QUESTION_ID = "intent"
INSTRUCTIONS = "Which category best matches this user request's intent?"


class SelfEvolvingRouter:
    def __init__(
        self,
        proposer: LLMCategoryProposer,
        confidence_threshold: float = 0.5,
        laya_model: str = "aac6fef/laya-mlx",
        batch_size: int = 10,
        backend: str = "mlx",
    ) -> None:
        self.registry = CategoryRegistry()
        self.proposer = proposer
        self.threshold = confidence_threshold
        self.batch_size = batch_size
        self.backend = backend
        self._agent = self._load_laya(laya_model)
        self.llm_calls = 0

    def _load_laya(self, model_id: str):
        if self.backend == "coreml":
            import laya_coreml as laya
            agent = laya.load(model_id)
        else:
            import laya_mlx as laya
            agent = laya.load(model_id, dtype="float16")
        return agent

    # -- question construction ------------------------------------------------
    def _question(self) -> dict:
        return {
            QUESTION_ID: {
                "type": "choice",
                "instructions": INSTRUCTIONS,
                "criteria": self._criteria(),
            }
        }

    def _criteria(self) -> dict[str, str]:
        criteria = {c.name: c.description for c in self.registry.all()}
        criteria[OTHER] = "none of the other options fit this request"
        return criteria

    # -- routing --------------------------------------------------------------
    def route(self, prompt_id: str, text: str, step: int) -> dict:
        """Routes one prompt; returns an event dict. Never raises on 'other'."""
        t0 = time.perf_counter()
        result = self._agent.predict(text, self._question())
        latency_ms = (time.perf_counter() - t0) * 1000
        answer = result["answers"][QUESTION_ID]
        choice = answer["choice"]

        if choice != OTHER and answer["confidence"] < self.threshold:
            route, reason = OTHER, "low_confidence"
        elif choice == OTHER:
            route, reason = OTHER, "other_bucket"
        else:
            route, reason = choice, "classified"

        usage = result.get("usage", {})
        return {
            "id": prompt_id,
            "text": text,
            "laya_choice": choice,
            "route": route,
            "reason": reason,
            "probs": answer["probabilities"],
            "latency_ms": round(latency_ms, 2),
            "input_tokens": usage.get("input_tokens", 0),
            "categories_at_route": len(self.registry.all()),
        }

    def learn_from_others(self, others: list[dict], step: int) -> list[dict]:
        """LLM proposes 1-2 categories from a batch of 'other' events."""
        if self.registry.is_full() or not others:
            return []
        batch = others[: self.proposer.batch_size]
        existing = [{"name": c.name, "description": c.description} for c in self.registry.all()]
        proposals = self.proposer.propose([o["text"] for o in batch], existing)
        self.llm_calls += 1
        created = []
        for p in proposals:
            cat = self.registry.add(p.name, p.description, step, [o["id"] for o in batch])
            if cat:
                created.append({
                    "step": step, "name": p.name, "description": p.description,
                    "from": [o["id"] for o in batch],
                })
        return created

    def stats(self) -> dict:
        return {
            "backend": self.backend,
            "categories": self.registry.names(),
            "llm_calls": self.llm_calls,
        }
