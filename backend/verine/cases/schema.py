"""Resilience Case File contract — the exportable, replayable decision artifact."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..common.ids import validate_id


class CaseFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_file_id: str
    case_type: str = "synthetic_crisis_replay"
    scenario_id: str
    graph_hash: str
    scenario_hash: str
    run_hash: str
    model_versions: list[str]
    seed: int
    executed_at: str
    capability_status: str
    impact_timeline: list[dict] = Field(default_factory=list)
    blast_radius: dict = Field(default_factory=dict)
    top_pathways: list[dict] = Field(default_factory=list)
    containment_sets: list[dict] = Field(default_factory=list)
    model_disagreement: dict = Field(default_factory=dict)
    evidence_requests: list[dict] = Field(default_factory=list)
    unknowns: list[dict] = Field(default_factory=list)
    assumptions: list[dict] = Field(default_factory=list)
    metrics: dict = Field(default_factory=dict)
    replay_command: str = ""
    disclaimer: str = (
        "Synthetic simulation over a fixture graph. Model results, not predictions "
        "about any real organization."
    )

    @field_validator("case_file_id")
    @classmethod
    def _id(cls, v: str) -> str:
        return validate_id(v, "case")

    @field_validator("graph_hash", "scenario_hash", "run_hash")
    @classmethod
    def _hashes(cls, v: str) -> str:
        if not v.startswith("sha256:"):
            raise ValueError("Hashes must be sha256-prefixed")
        return v
