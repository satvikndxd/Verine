"""Capability contract: a business service with a measurable service level."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ..common.enums import Criticality
from ..common.ids import validate_id


class Capability(BaseModel):
    model_config = ConfigDict(extra="forbid")

    capability_id: str
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    owner_role: str = Field(min_length=1)
    minimum_service_level: float = Field(ge=0, le=1)
    target_service_level: float = Field(ge=0, le=1)
    unit: str = Field(min_length=1)
    criticality: Criticality
    valid_from: str
    valid_to: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)

    @field_validator("capability_id")
    @classmethod
    def _id(cls, v: str) -> str:
        return validate_id(v, "capability")

    @model_validator(mode="after")
    def _levels(self) -> "Capability":
        if self.minimum_service_level > self.target_service_level:
            raise ValueError("minimum_service_level cannot exceed target_service_level")
        return self
