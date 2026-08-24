"""Provider registry: typed discovery of LLM and live-connector adapters."""

from __future__ import annotations

from .llm.anthropic import AnthropicProvider
from .llm.ollama import OllamaProvider
from .llm.openai import OpenAIProvider
from .llm.openai_compatible import OpenAICompatibleProvider
from .llm.openrouter import OpenRouterProvider

LLM_PROVIDER_CLASSES = {
    "openrouter": OpenRouterProvider,
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "openai_compatible": OpenAICompatibleProvider,
    "ollama_local": OllamaProvider,
}


def llm_provider(provider_id: str, transport=None):
    cls = LLM_PROVIDER_CLASSES.get(provider_id)
    if cls is None:
        raise KeyError(f"Unknown LLM provider {provider_id!r}")
    return cls(transport=transport)


def provider_catalog() -> list[dict]:
    return [
        {"provider_id": "openrouter", "protocol": "openai_compatible",
         "base_url": "https://openrouter.ai/api/v1", "needs_key": True},
        {"provider_id": "openai", "protocol": "openai_compatible",
         "base_url": "https://api.openai.com/v1", "needs_key": True},
        {"provider_id": "anthropic", "protocol": "anthropic_messages",
         "base_url": "https://api.anthropic.com", "needs_key": True},
        {"provider_id": "openai_compatible", "protocol": "openai_compatible",
         "base_url": None, "needs_key": True,
         "note": "Custom endpoint; SSRF-guarded; requires explicit confirmation"},
        {"provider_id": "ollama_local", "protocol": "openai_compatible",
         "base_url": "http://127.0.0.1:11434/v1", "needs_key": False},
    ]


def live_connector_catalog() -> list[dict]:
    from .live.registry import LIVE_CONNECTOR_CLASSES

    return [
        {"connector_type": ct, "adapter_version": cls.adapter_version}
        for ct, cls in LIVE_CONNECTOR_CLASSES.items()
    ]
