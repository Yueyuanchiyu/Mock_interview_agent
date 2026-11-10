from __future__ import annotations

import math
from typing import Iterable, List

from app.core.config import settings


class ContextBudget:
    """Conservative token estimator used before prompt assembly."""

    def __init__(self, max_tokens: int | None = None) -> None:
        self.max_tokens = max_tokens or settings.context_max_tokens

    @staticmethod
    def estimate_tokens(text: str) -> int:
        ascii_chars = sum(1 for char in text if ord(char) < 128)
        non_ascii_chars = len(text) - ascii_chars
        return max(1, math.ceil(ascii_chars / 4 + non_ascii_chars))

    def trim(self, text: str, max_tokens: int | None = None) -> str:
        text = (text or "").strip()
        budget = max_tokens or self.max_tokens
        if self.estimate_tokens(text) <= budget:
            return text
        if budget <= 1:
            return text[:1]
        low, high = 0, len(text)
        while low < high:
            mid = (low + high + 1) // 2
            if self.estimate_tokens(text[:mid]) <= budget:
                low = mid
            else:
                high = mid - 1
        return text[:low].rstrip() + "…"

    def pack(self, items: Iterable[str], reserved_tokens: int = 500) -> List[str]:
        remaining = max(1, self.max_tokens - reserved_tokens)
        packed: List[str] = []
        for item in items:
            clean = (item or "").strip()
            if not clean:
                continue
            estimated = self.estimate_tokens(clean)
            if estimated <= remaining:
                packed.append(clean)
                remaining -= estimated
                continue
            if remaining > 64:
                packed.append(self.trim(clean, remaining))
            break
        return packed

