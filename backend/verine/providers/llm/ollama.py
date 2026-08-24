"""Ollama local adapter — OpenAI-compatible endpoint on localhost.

Localhost is intentionally allowed here (local inference, no key required)."""

from __future__ import annotations

from .openai_compatible import OpenAICompatibleProvider


class OllamaProvider(OpenAICompatibleProvider):
    provider_id = "ollama_local"
    adapter_version = "ollama@0.1.0"
    default_base_url = "http://127.0.0.1:11434/v1"
    require_url_validation = False  # local by definition; no SSRF surface

    def _headers(self, api_key: str | None) -> dict:
        return {"Content-Type": "application/json"}  # no key needed
