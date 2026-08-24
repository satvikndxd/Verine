"""Seeded RNG wrapper. The ONLY permitted source of randomness in simulations.

Sub-streams are derived deterministically from (seed, label) so Monte Carlo
replications are independent of iteration order.
"""

from __future__ import annotations

import hashlib
import random


class SeededRng:
    def __init__(self, seed: int, label: str = "root") -> None:
        self.seed = int(seed)
        self.label = label
        material = hashlib.sha256(f"{self.seed}:{label}".encode()).digest()
        self._rng = random.Random(int.from_bytes(material[:8], "big"))

    def substream(self, label: str) -> "SeededRng":
        return SeededRng(self.seed, f"{self.label}/{label}")

    def uniform(self, low: float, high: float) -> float:
        return self._rng.uniform(low, high)

    def triangular(self, low: float, mode: float, high: float) -> float:
        if low == high:
            return low
        return self._rng.triangular(low, high, mode)
