"""Scenario contract: graph snapshot + incident + constraints + seed + models."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..common.hashing import hash_obj
from ..common.ids import validate_id

KNOWN_MODELS = {"reachability_v1", "deterministic_propagation_v1", "capacity_flow_v1", "monte_carlo_v1"}

MAX_HORIZON_MINUTES = 7 * 24 * 60  # safety cap
MAX_MONTE_CARLO_REPLICATIONS = 500  # safety cap


class ScenarioConstraints(BaseModel):
    model_config = ConfigDict(extra="forbid")

    budget: float = Field(ge=0)
    deadline_minutes: int = Field(gt=0)
    minimum_service_level: float = Field(ge=0, le=1)
    available_roles: list[str] = Field(default_factory=list)
    max_collateral_risk: float = Field(default=1.0, ge=0, le=1)
    facts: list[str] = Field(default_factory=list, description="Feasibility facts, e.g. 'backup_contract_active'")


class ScheduledAction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action_id: str
    start_minutes: int = Field(ge=0)


class Scenario(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_id: str
    capability_id: str
    graph_snapshot_id: str
    incident_id: str
    constraints: ScenarioConstraints
    scheduled_actions: list[ScheduledAction] = Field(default_factory=list)
    hidden_edge_ids: list[str] = Field(
        default_factory=list,
        description="Edges hidden from models to emulate incomplete topology; increases unknown risk",
    )
    seed: int
    horizon_minutes: int = Field(default=1440, gt=0, le=MAX_HORIZON_MINUTES)
    step_minutes: int = Field(default=5, gt=0)
    monte_carlo_replications: int = Field(default=100, gt=0, le=MAX_MONTE_CARLO_REPLICATIONS)
    model_set: list[str] = Field(min_length=1)
    created_at: str

    @field_validator("scenario_id")
    @classmethod
    def _id(cls, v: str) -> str:
        return validate_id(v, "scenario")

    @field_validator("model_set")
    @classmethod
    def _models(cls, v: list[str]) -> list[str]:
        unknown = sorted(set(v) - KNOWN_MODELS)
        if unknown:
            raise ValueError(f"Unknown models: {unknown}. Known: {sorted(KNOWN_MODELS)}")
        return v

    def scenario_hash(self) -> str:
        # Identity is the semantic inputs, not creation time or the id. This keeps
        # two scenarios with identical inputs (e.g. re-built forks) hash-equal and
        # therefore byte-for-byte replayable.
        payload = self.model_dump(mode="json")
        payload.pop("created_at", None)
        payload.pop("scenario_id", None)
        return hash_obj(payload)
