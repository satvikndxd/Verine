"""Structured uncertainty. Never a single fake confidence number."""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class Interval(BaseModel):
    low: float
    median: float
    high: float

    @model_validator(mode="after")
    def _ordered(self) -> "Interval":
        if not (self.low <= self.median <= self.high):
            raise ValueError("Interval must satisfy low <= median <= high")
        return self


class Uncertainty(BaseModel):
    aleatoric: float = Field(ge=0, le=1)
    epistemic: float = Field(ge=0, le=1)
    observability: float = Field(ge=0, le=1)
    model_disagreement: float = Field(ge=0, le=1)
    interval: Interval
    explanation: str

    def reliability_label(self) -> str:
        worst = max(self.epistemic, self.model_disagreement, 1 - self.observability)
        if worst < 0.2:
            return "reasonable"
        if worst < 0.45:
            return "limited"
        return "weak"
