"""Incident contract, including compound incidents."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ..common.enums import EpistemicStatus, IncidentMode, IncidentType
from ..common.ids import validate_id
from ..common.time import parse_utc
from ..common.uncertainty import Interval


class IncidentComponent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_node_id: str
    mode: IncidentMode
    severity: float = Field(ge=0, le=1)
    severity_interval: Interval | None = Field(
        default=None, description="Declared uncertainty interval for Monte Carlo sampling"
    )
    duration_minutes: int = Field(gt=0)
    duration_interval_minutes: Interval | None = Field(
        default=None, description="Declared uncertainty interval for Monte Carlo sampling"
    )
    onset_offset_minutes: int = Field(default=0, ge=0)
    evidence_status: EpistemicStatus = EpistemicStatus.SIMULATED


class Incident(BaseModel):
    model_config = ConfigDict(extra="forbid")

    incident_id: str
    name: str = Field(min_length=1)
    incident_type: IncidentType
    onset_at: str
    duration_minutes: int = Field(gt=0)
    severity: float = Field(ge=0, le=1)
    components: list[IncidentComponent] = Field(min_length=1)
    evidence_ids: list[str] = Field(default_factory=list)

    @field_validator("incident_id")
    @classmethod
    def _id(cls, v: str) -> str:
        return validate_id(v, "incident")

    @field_validator("onset_at")
    @classmethod
    def _onset(cls, v: str) -> str:
        parse_utc(v)
        return v

    @model_validator(mode="after")
    def _consistent(self) -> "Incident":
        if self.incident_type == IncidentType.COMPOUND and len(self.components) < 2:
            raise ValueError("Compound incidents require at least two components")
        span = max(c.onset_offset_minutes + c.duration_minutes for c in self.components)
        if span > self.duration_minutes:
            raise ValueError(
                f"Component window ({span}m) exceeds incident duration_minutes ({self.duration_minutes}m)"
            )
        return self
