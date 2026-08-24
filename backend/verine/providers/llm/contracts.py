"""LLM gateway contracts. The LLM is optional and subordinate to deterministic
evidence — it explains structured outputs and can never create incident state."""

from __future__ import annotations

from typing import AsyncIterator, Protocol

from pydantic import BaseModel, ConfigDict, Field

LLM_TASKS = [
    "evidence_extract",
    "signal_explain",
    "incident_summarize",
    "pathway_narrate",
    "entity_alias_suggest",
    "evidence_gap",
    "case_qa",
]


class ModelInfo(BaseModel):
    model_config = ConfigDict(extra="allow")
    model_id: str
    name: str = ""
    context_length: int | None = None
    prompt_cost_per_mtok: float | None = None  # None => COST UNKNOWN
    completion_cost_per_mtok: float | None = None


class ProviderHealth(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider_id: str
    status: str  # "success" | "auth_error" | "unreachable" | "error"
    detail: str = ""
    checked_at: str = ""


class LLMMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: str  # system | user | assistant
    content: str


class LLMRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: str
    provider_id: str
    model: str
    task: str
    messages: list[LLMMessage]
    temperature: float = Field(default=0.1, ge=0, le=2)
    max_output_tokens: int = Field(default=1200, gt=0, le=8000)
    stream: bool = False
    response_format: str = "structured_json"  # or "text"
    json_schema_name: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    case_id: str | None = None
    prompt_version: str = "v1"
    budget_cents: int = Field(default=10, ge=0)


class LLMResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: str
    provider_id: str
    model: str
    content: str
    structured: dict | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    estimated_cost_cents: float | None = None  # None => unknown
    prompt_hash: str = ""
    response_hash: str = ""
    validation: dict = Field(default_factory=dict)


class LLMChunk(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: str
    delta: str = ""
    done: bool = False
    error: str | None = None


class LLMProvider(Protocol):
    provider_id: str
    adapter_version: str

    async def list_models(self, api_key: str | None, base_url: str | None) -> list[ModelInfo]: ...

    async def health_check(self, api_key: str | None, base_url: str | None) -> ProviderHealth: ...

    async def complete(
        self, request: LLMRequest, api_key: str | None, base_url: str | None
    ) -> LLMResponse: ...

    def stream(
        self, request: LLMRequest, api_key: str | None, base_url: str | None
    ) -> AsyncIterator[LLMChunk]: ...
