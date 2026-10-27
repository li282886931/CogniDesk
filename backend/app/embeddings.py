from __future__ import annotations

import hashlib
import math
import re
from typing import Protocol


class EmbeddingProvider(Protocol):
    dimension: int

    def embed(self, text: str) -> list[float]:
        ...


class DeterministicEmbeddingProvider:
    """Small local provider for development and tests.

    It is deterministic and content-sensitive, but is not a substitute for a
    production semantic embedding model.
    """

    def __init__(self, dimension: int = 32):
        if dimension < 2:
            raise ValueError("dimension must be at least 2")
        self.dimension = dimension

    def embed(self, text: str) -> list[float]:
        normalized = text.strip()
        if not normalized:
            raise ValueError("text must not be blank")

        tokens = re.findall(r"\w|[^\w\s]", normalized, flags=re.UNICODE)
        vector = [0.0] * self.dimension
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimension
            vector[index] += 1.0 if digest[4] & 1 else -1.0

        magnitude = math.sqrt(sum(value * value for value in vector))
        if magnitude == 0:
            vector[0] = 1.0
            magnitude = 1.0
        return [value / magnitude for value in vector]
