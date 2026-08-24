"""OpenRouter adapter — OpenAI-compatible protocol at https://openrouter.ai/api/v1.

Ref: OpenRouter API reference (base URL, /models, /chat/completions, Bearer auth,
SSE streaming). Optional attribution headers are configured, never hard-coded.
"""

from __future__ import annotations

import os

from .openai_compatible import OpenAICompatibleProvider


class OpenRouterProvider(OpenAICompatibleProvider):
    provider_id = "openrouter"
    adapter_version = "openrouter@0.1.0"
    default_base_url = "https://openrouter.ai/api/v1"
    require_url_validation = False  # fixed public host

    def _headers(self, api_key: str | None) -> dict:
        h = super()._headers(api_key)
        referer = os.environ.get("VERINE_OPENROUTER_REFERER", "")
        title = os.environ.get("VERINE_OPENROUTER_TITLE", "VERINE")
        if referer:
            h["HTTP-Referer"] = referer
        if title:
            h["X-OpenRouter-Title"] = title
        return h
