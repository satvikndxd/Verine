"""Simulation state and result containers. Every step serializes deterministically."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from ..common.hashing import hash_obj


class StepState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    t_minutes: int
    service_levels: dict[str, float]
    node_degradation: dict[str, float]
    active_incident_nodes: list[str]
    effective_actions: list[str]


class ImpactEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    impact_event_id: str
    source_node_id: str
    source_kind: str  # "incident" | "dependency_edge"
    via_edge_id: str | None = None
    target_node_id: str
    impact_type: str = "service_level_reduction"
    impact_start_minutes: int
    impact_end_minutes: int | None = None
    magnitude: float
    rule: str
    model_id: str
    epistemic_status: str = "model_result"
    assumption_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)


class Pathway(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pathway_id: str
    node_chain: list[str]
    edge_chain: list[str]
    strength: float
    first_impact_minutes: int
    description: str


class PropagationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_id: str
    seed: int
    steps: list[StepState]
    impact_events: list[ImpactEvent]
    pathways: list[Pathway]
    metrics: dict
    assumptions: list[dict] = Field(default_factory=list)
    epistemic_status: str = "model_result"

    def result_hash(self) -> str:
        return hash_obj(self.model_dump(mode="json"))
