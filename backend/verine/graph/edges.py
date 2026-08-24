"""Dependency edge contract.

Direction convention (documented, enforced by the engine):
an edge `from_node -> to_node` of type `requires`/`calls`/... means the
FROM node depends on the TO node. Impact therefore propagates in REVERSE
edge direction: degradation of `to_node` impacts `from_node`.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..common.enums import EdgeType, EpistemicStatus
from ..common.ids import is_valid_id


class LagMinutes(BaseModel):
    model_config = ConfigDict(extra="forbid")
    min: float = Field(ge=0)
    median: float = Field(ge=0)
    max: float = Field(ge=0)

    @field_validator("max")
    @classmethod
    def _ordered(cls, v: float, info) -> float:
        lo = info.data.get("min", 0)
        med = info.data.get("median", 0)
        if not (lo <= med <= v):
            raise ValueError("lag must satisfy min <= median <= max")
        return v


class Edge(BaseModel):
    model_config = ConfigDict(extra="forbid")

    edge_id: str
    from_node: str
    to_node: str
    edge_type: EdgeType
    criticality_weight: float = Field(ge=0, le=1)
    capacity_fraction: float = Field(default=1.0, ge=0, le=1)
    propagation_lag_minutes: LagMinutes = Field(default_factory=lambda: LagMinutes(min=0, median=0, max=0))
    substitution_options: list[str] = Field(default_factory=list)
    epistemic_status: EpistemicStatus = EpistemicStatus.OBSERVED
    confidence: float = Field(default=1.0, ge=0, le=1)
    evidence_ids: list[str] = Field(default_factory=list)

    @field_validator("edge_id", "from_node", "to_node")
    @classmethod
    def _ids(cls, v: str) -> str:
        if not is_valid_id(v):
            raise ValueError(f"Invalid id {v!r}")
        return v
