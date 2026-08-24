"""Dependency node contract."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..common.enums import Criticality, EpistemicStatus, NodeStatus, NodeType
from ..common.ids import is_valid_id
from ..common.uncertainty import Interval


class Node(BaseModel):
    model_config = ConfigDict(extra="forbid")

    node_id: str
    node_type: NodeType
    name: str = Field(min_length=1)
    criticality: Criticality = Criticality.MEDIUM
    capacity: float | None = Field(default=None, gt=0)
    capacity_unit: str | None = None
    recovery_time_minutes: int = Field(default=60, ge=0)
    recovery_time_interval_minutes: Interval | None = Field(
        default=None, description="Declared uncertainty interval for Monte Carlo sampling"
    )
    substitutability: float = Field(default=0.0, ge=0, le=1)
    observability: float = Field(default=1.0, ge=0, le=1)
    status: NodeStatus = NodeStatus.HEALTHY
    epistemic_status: EpistemicStatus = EpistemicStatus.OBSERVED
    evidence_ids: list[str] = Field(default_factory=list)

    @field_validator("node_id")
    @classmethod
    def _id(cls, v: str) -> str:
        if not is_valid_id(v):
            raise ValueError(f"Invalid node_id {v!r}")
        return v
