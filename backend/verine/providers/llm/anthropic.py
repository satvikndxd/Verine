"""Anthropic adapter — translates the gateway contract to the Messages API."""

from __future__ import annotations

import json
from typing import AsyncIterator

import httpx

from ...common.hashing import hash_obj
from ...common.redaction import redact_text
from .contracts import LLMChunk, LLMRequest, LLMResponse, ModelInfo, ProviderHealth
from .openai_compatible import DEFAULT_TIMEOUT, ProviderError, _check, _now


class AnthropicProvider:
    provider_id = "anthropic"
    adapter_version = "anthropic@0.1.0"
    default_base_url = "https://api.anthropic.com"

    def __init__(self, transport: httpx.AsyncBaseTransport | None = None):
        self._transport = transport

    def _headers(self, api_key: str | None) -> dict:
        return {
            "Content-Type": "application/json",
            "x-api-key": api_key or "",
            "anthropic-version": "2023-06-01",
        }

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=self._transport, timeout=DEFAULT_TIMEOUT, follow_redirects=False)

    def _base(self, base_url: str | None) -> str:
        return (base_url or self.default_base_url).rstrip("/")

    @staticmethod
    def _translate(request: LLMRequest) -> dict:
        """Split system messages out; merge into Anthropic message format."""
        system_parts = [m.content for m in request.messages if m.role == "system"]
        messages = [
            {"role": m.role, "content": m.content} for m in request.messages if m.role != "system"
        ]
        payload = {
            "model": request.model,
            "max_tokens": request.max_output_tokens,
            "temperature": request.temperature,
            "messages": messages or [{"role": "user", "content": ""}],
        }
        if system_parts:
            payload["system"] = "\n\n".join(system_parts)
        return payload

    async def list_models(self, api_key: str | None, base_url: str | None) -> list[ModelInfo]:
        async with self._client() as client:
            r = await client.get(f"{self._base(base_url)}/v1/models", headers=self._headers(api_key))
            _check(r)
            data = r.json().get("data", [])
        return [ModelInfo(model_id=m.get("id", ""), name=m.get("display_name", m.get("id", ""))) for m in data]

    async def health_check(self, api_key: str | None, base_url: str | None) -> ProviderHealth:
        try:
            models = await self.list_models(api_key, base_url)
            return ProviderHealth(provider_id=self.provider_id, status="success",
                                  detail=f"{len(models)} models visible", checked_at=_now())
        except ProviderError as e:
            status = "auth_error" if "401" in str(e) or "403" in str(e) else "error"
            return ProviderHealth(provider_id=self.provider_id, status=status,
                                  detail=redact_text(str(e)), checked_at=_now())
        except httpx.HTTPError as e:
            return ProviderHealth(provider_id=self.provider_id, status="unreachable",
                                  detail=redact_text(str(e)), checked_at=_now())

    async def complete(self, request: LLMRequest, api_key: str | None, base_url: str | None) -> LLMResponse:
        async with self._client() as client:
            r = await client.post(
                f"{self._base(base_url)}/v1/messages",
                headers=self._headers(api_key),
                json=self._translate(request),
            )
            _check(r)
            body = r.json()
        content = "".join(b.get("text", "") for b in body.get("content", []) if b.get("type") == "text")
        usage = body.get("usage") or {}
        return LLMResponse(
            request_id=request.request_id,
            provider_id=self.provider_id,
            model=body.get("model", request.model),
            content=content,
            prompt_tokens=usage.get("input_tokens"),
            completion_tokens=usage.get("output_tokens"),
            prompt_hash=hash_obj([m.model_dump() for m in request.messages]),
            response_hash=hash_obj(content),
        )

    async def stream(
        self, request: LLMRequest, api_key: str | None, base_url: str | None
    ) -> AsyncIterator[LLMChunk]:
        payload = self._translate(request)
        payload["stream"] = True
        async with self._client() as client:
            async with client.stream(
                "POST", f"{self._base(base_url)}/v1/messages",
                headers=self._headers(api_key), json=payload,
            ) as r:
                if r.status_code >= 400:
                    detail = (await r.aread())[:400].decode(errors="replace")
                    yield LLMChunk(request_id=request.request_id, done=True,
                                   error=redact_text(f"HTTP {r.status_code}: {detail}"))
                    return
                async for line in r.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    try:
                        evt = json.loads(line[5:].strip())
                    except json.JSONDecodeError:
                        continue
                    if evt.get("type") == "content_block_delta":
                        delta = evt.get("delta", {}).get("text", "")
                        if delta:
                            yield LLMChunk(request_id=request.request_id, delta=delta)
        yield LLMChunk(request_id=request.request_id, done=True)
