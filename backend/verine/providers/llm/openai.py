"""OpenAI adapter — OpenAI protocol at the official endpoint."""

from __future__ import annotations

from .openai_compatible import OpenAICompatibleProvider


class OpenAIProvider(OpenAICompatibleProvider):
    provider_id = "openai"
    adapter_version = "openai@0.1.0"
    default_base_url = "https://api.openai.com/v1"
    require_url_validation = False
