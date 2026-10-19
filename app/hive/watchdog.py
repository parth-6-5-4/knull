"""Plain-code watchdog and budget governor (not an LLM; Book 1 ch. 14.2 / 14.6)."""
from __future__ import annotations

import re


def _tokens(s: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", s.lower()))


def similarity(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    if not ta and not tb:
        return 1.0
    return len(ta & tb) / max(1, len(ta | tb))


def is_looping(outputs: list[str], threshold: float = 0.9, window: int = 2) -> bool:
    """True if the last `window` outputs are near-repeats of the one before (exact or paraphrased)."""
    if len(outputs) < window + 1:
        return False
    last = outputs[-1]
    return all(similarity(last, o) >= threshold for o in outputs[-1 - window:-1])


class BudgetGovernor:
    """Hard token cap: refuses new LLM calls once the ledger reaches the cap."""

    def __init__(self, store, run_id: str, cap_tokens: int):
        self.store, self.run_id, self.cap = store, run_id, cap_tokens

    def spent(self) -> int:
        return self.store.spent(self.run_id)

    def exhausted(self) -> bool:
        return self.cap > 0 and self.spent() >= self.cap
