"""Self-evolving prompt router built on laya-mlx.

Laya answers typed decisions (choice/score/noul) in ~10-20 ms locally.
This package orchestrates a router whose category set grows over time:
prompts that Laya cannot classify (or classifies with low confidence) land
in "other", are batched, and an LLM proposes new categories that Laya can
then use.
"""

from .router import SelfEvolvingRouter
from .simulation import run_simulation

__all__ = ["SelfEvolvingRouter", "run_simulation"]
