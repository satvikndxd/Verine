"""Containment action contract."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..common.enums import ActionType, EpistemicStatus
from ..common.ids import validate_id


class Action(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_id: str
    name: str = Field(min_length=1)
    action_type: ActionType
    target_nodes: list[str] = Field(min_length=1)
    affected_capabilities: list[str] = Field(default_factory=list)
    cost: float = Field(ge=0)
    duration_minutes: int = Field(ge=0)
    required_roles: list[str] = Field(default_factory=list)
    capacity_effect: float = Field(ge=0, le=1, description="Fraction of target degradation removed once effective")
    reversibility: float = Field(ge=0, le=1)
    collateral_risk: float = Field(ge=0, le=1)
    evidence_status: str = "fixture_action"
    feasibility_constraints: list[str] = Field(default_factory=list)
    side_effects: list[str] = Field(default_factory=list)
    epistemic_status: EpistemicStatus = EpistemicStatus.SIMULATED

    @field_validator("action_id")
    @classmethod
    def _id(cls, v: str) -> str:
        return validate_id(v, "action")
