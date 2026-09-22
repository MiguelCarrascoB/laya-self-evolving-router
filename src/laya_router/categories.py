"""Category registry for the evolving router."""

from __future__ import annotations

from dataclasses import dataclass, field

MAX_CATEGORIES = 30  # cap: 512-token Laya context bounds the option list size


@dataclass
class Category:
    name: str
    description: str  # one-line criteria passed to Laya
    created_at_step: int
    created_from: list[str] = field(default_factory=list)  # prompt ids
    seeded: bool = False


class CategoryRegistry:
    """Grows monotonically; duplicates (by similar name) are rejected."""

    def __init__(self, max_categories: int = MAX_CATEGORIES) -> None:
        self._cats: list[Category] = []
        self._max = max_categories
        self.rejections: list[dict] = []
        self.seed_rejections: list[dict] = []

    def all(self) -> list[Category]:
        return list(self._cats)

    def names(self) -> list[str]:
        return [c.name for c in self._cats]

    def is_full(self) -> bool:
        return len(self._cats) >= self._max

    @staticmethod
    def _norm(s: str) -> str:
        out = s.lower()
        for ch in ("-", "_", " ", "-"):
            out = out.replace(ch, "")
        return out

    def has_similar(self, name: str) -> bool:
        n = self._norm(name)
        for c in self._cats:
            cn = self._norm(c.name)
            if n == cn or (len(n) > 4 and n in cn) or (len(cn) > 4 and cn in n):
                return True
        return False

    def add(self, name: str, description: str, step: int, source_ids: list[str]) -> Category | None:
        """Returns the new Category, or None if duplicate / cap reached."""
        if self.is_full():
            self.rejections.append(
                {"name": name, "reason": "cap", "step": step, "source_ids": list(source_ids)}
            )
            return None
        if self.has_similar(name):
            self.rejections.append(
                {"name": name, "reason": "duplicate", "step": step, "source_ids": list(source_ids)}
            )
            return None
        cat = Category(name=name, description=description, created_at_step=step, created_from=source_ids)
        self._cats.append(cat)
        return cat

    def seed(
        self, name: str, description: str, step: int = 0, source_ids: tuple[str, ...] = ()
    ) -> Category | None:
        """Insert an initial category, applying the same cap and duplicate gates as ``add``."""
        if self.is_full():
            self.seed_rejections.append(
                {"name": name, "reason": "cap", "step": step, "source_ids": list(source_ids)}
            )
            return None
        if self.has_similar(name):
            self.seed_rejections.append(
                {"name": name, "reason": "duplicate", "step": step, "source_ids": list(source_ids)}
            )
            return None
        cat = Category(
            name=name,
            description=description,
            created_at_step=step,
            created_from=list(source_ids),
            seeded=True,
        )
        self._cats.append(cat)
        return cat

    def as_dicts(self) -> list[dict]:
        return [
            {
                "name": c.name,
                "description": c.description,
                "created_at_step": c.created_at_step,
                "created_from": c.created_from,
                "seeded": c.seeded,
            }
            for c in self._cats
        ]

    def growth_history(self) -> list[dict]:
        return [{"step": c.created_at_step, "name": c.name, "from": c.created_from} for c in self._cats]
