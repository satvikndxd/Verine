"""Credential contracts. Plaintext is NEVER serialized.

`Credential` (stored form) holds ciphertext only. `CredentialMeta` (API form)
holds masked metadata only. Plaintext exists solely as a function-local value
inside the gateway request path and is registered with the redactor.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

SUPPORTED_LLM_PROVIDERS = ["openrouter", "openai", "anthropic", "openai_compatible", "ollama_local"]


class Credential(BaseModel):
    """Stored form — ciphertext only."""

    model_config = ConfigDict(extra="forbid")

    credential_id: str
    provider_id: str
    label: str = ""
    key_last4: str = ""
    ciphertext: str  # base64
    salt: str  # base64
    nonce: str  # base64
    encryption_version: str = "vault_v1"
    created_at: str
    updated_at: str
    last_tested_at: str | None = None
    last_test_status: str = "untested"
    usage_budget_cents: int = 500
    base_url: str | None = None  # for openai_compatible / ollama
    default_model: str | None = None
    enabled: bool = True

    def to_meta(self) -> "CredentialMeta":
        return CredentialMeta(
            credential_id=self.credential_id,
            provider_id=self.provider_id,
            label=self.label,
            masked=("•" * 12 + self.key_last4) if self.key_last4 else "(no key)",
            enabled=self.enabled,
            last_tested_at=self.last_tested_at,
            last_test_status=self.last_test_status,
            usage_budget_cents=self.usage_budget_cents,
            base_url=self.base_url,
            default_model=self.default_model,
            created_at=self.created_at,
        )


class CredentialMeta(BaseModel):
    """API response form — metadata only, never key material."""

    model_config = ConfigDict(extra="forbid")

    credential_id: str
    provider_id: str
    label: str
    masked: str
    enabled: bool
    last_tested_at: str | None
    last_test_status: str
    usage_budget_cents: int
    base_url: str | None
    default_model: str | None
    created_at: str


class CredentialCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_id: str
    api_key: str = Field(min_length=0, max_length=512, repr=False)
    label: str = ""
    usage_budget_cents: int = Field(default=500, ge=0, le=100_000)
    base_url: str | None = None
    default_model: str | None = None
