"""External signal and live-evidence contracts (master prompt §8.3, §8.4)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

SIGNAL_TYPES = [
    "provider_incident",
    "provider_maintenance",
    "vulnerability_kev",
    "vulnerability_cve",
    "weather_alert",
    "regulatory_filing",
    "advisory",
]

SEVERITIES = ["info", "low", "medium", "high", "critical"]

IMPACT_STATUSES = [
    "external_signal_only",
    "possible_exposure",
    "projected_capability_impact",
    "user_confirmed_impact",
]


class ExternalSignal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    signal_id: str
    provider_id: str
    connector_type: str
    source_uri: str
    source_event_id: str
    signal_type: str
    title: str
    summary: str = ""
    event_at: str | None = None
    published_at: str
    updated_at: str | None = None
    retrieved_at: str
    valid_from: str | None = None
    valid_to: str | None = None
    severity: str = "medium"
    entities: list[str] = Field(default_factory=list)
    geographies: list[str] = Field(default_factory=list)
    raw_artifact_hash: str = ""
    normalized_hash: str = ""
    epistemic_status: str = "observed"
    impact_status: str = "external_signal_only"
    evidence_ids: list[str] = Field(default_factory=list)
    parser_version: str = ""


class LiveEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_id: str
    statement: str
    source_uri: str
    source_event_id: str = ""
    retrieved_at: str
    published_at: str | None = None
    locator: dict = Field(default_factory=dict)
    content_hash: str = ""
    source_independence_group: str = ""
    epistemic_status: str = "observed"
    terms_status: str = "public_api"
    contradicts: list[str] = Field(default_factory=list)
    parser_version: str = ""
