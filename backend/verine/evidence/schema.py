"""Evidence and assumption records with provenance."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from ..common.enums import EpistemicStatus


class Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_id: str
    label: str
    epistemic_status: EpistemicStatus
    source_uri: str | None = None
    locator: dict = Field(default_factory=dict)
    content_hash: str | None = None
    statement: str


class Assumption(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assumption_id: str
    statement: str
    epistemic_status: EpistemicStatus = EpistemicStatus.HYPOTHESIS
    supports: list[str] = Field(default_factory=list)
