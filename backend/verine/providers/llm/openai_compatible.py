"""OpenAI-compatible chat adapter — the shared engine for OpenRouter, OpenAI,
and custom endpoints. Differences are base URL, headers, and safety policy.

Custom endpoints (provider_id=openai_compatible) get SSRF protection:
- https required in deployed mode
- private/loopback/link-local addresses blocked unless
  VERINE_ALLOW_PRIVATE_PROVIDER_HOSTS=1 (local mode)
- redirects are not followed
"""

from __future__ import annotations

import ipaddress
import json
import os
import socket
from datetime import datetime, timezone
from typing import AsyncIterator
from urllib.parse import urlparse

import httpx

from ...common.errors import VerineError
from ...common.hashing import hash_obj
from ...common.redaction import redact_text
from .contracts import LLMChunk, LLMRequest, LLMResponse, ModelInfo, ProviderHealth

DEFAULT_TIMEOUT = 60.0
MAX_RESPONSE_BYTES = 4 * 1024 * 1024


class ProviderError(VerineError):
    error_code = "PROVIDER_ERROR"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def validate_provider_url(base_url: str, allow_private: bool | None = None) -> str:
    """SSRF guard for custom provider hosts."""
    if allow_private is None:
        allow_private = os.environ.get("VERINE_ALLOW_PRIVATE_PROVIDER_HOSTS", "0") == "1"
    parsed = urlparse(base_url)
    if parsed.scheme not in ("https", "http"):
        raise ProviderError(f"Unsupported URL scheme {parsed.scheme!r}")
    if parsed.scheme == "http" and not allow_private:
        raise ProviderError("http:// provider URLs require VERINE_ALLOW_PRIVATE_PROVIDER_HOSTS=1 (local mode)")
    host = parsed.hostname or ""
    if not host:
        raise ProviderError("Provider URL has no host")
    if not allow_private:
        try:
            infos = socket.getaddrinfo(host, None)
        except socket.gaierror as e:
            raise ProviderError(f"Cannot resolve provider host {host!r}: {e}") from e
        for info in infos:
            addr = ipaddress.ip_address(info[4][0])
            if addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved:
                raise ProviderError(
                    f"Provider host {host!r} resolves to a private address; blocked (SSRF protection)"
                )
    return base_url.rstrip("/")


class OpenAICompatibleProvider:
    provider_id = "openai_compatible"
    adapter_version = "openai_compatible@0.1.0"
    default_base_url: str | None = None
    require_url_validation = True

    def __init__(self, transport: httpx.AsyncBaseTransport | None = None):
        self._transport = transport  # injectable for tests

    def _headers(self, api_key: str | None) -> dict:
        h = {"Content-Type": "application/json"}
        if api_key:
            h["Authorization"] = f"Bearer {api_key}"
        return h

    def _base(self, base_url: str | None) -> str:
        base = base_url or self.default_base_url
        if not base:
            raise ProviderError("base_url is required for this provider")
        if self.require_url_validation:
            base = validate_provider_url(base)
        return base.rstrip("/")

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            transport=self._transport, timeout=DEFAULT_TIMEOUT, follow_redirects=False
        )

    async def list_models(self, api_key: str | None, base_url: str | None) -> list[ModelInfo]:
        async with self._client() as client:
            r = await client.get(f"{self._base(base_url)}/models", headers=self._headers(api_key))
            _check(r)
            data = r.json().get("data", [])
        models = []
        for m in data:
            pricing = m.get("pricing") or {}
            models.append(
                ModelInfo(
                    model_id=m.get("id", ""),
                    name=m.get("name", m.get("id", "")),
                    context_length=m.get("context_length"),
                    prompt_cost_per_mtok=_per_mtok(pricing.get("prompt")),
                    completion_cost_per_mtok=_per_mtok(pricing.get("completion")),
                )
            )
        return models

    async def health_check(self, api_key: str | None, base_url: str | None) -> ProviderHealth:
        try:
            models = await self.list_models(api_key, base_url)
            return ProviderHealth(
                provider_id=self.provider_id,
                status="success",
                detail=f"{len(models)} models visible",
                checked_at=_now(),
            )
        except ProviderError as e:
            status = "auth_error" if "401" in str(e) or "403" in str(e) else "error"
            return ProviderHealth(
                provider_id=self.provider_id, status=status, detail=redact_text(str(e)), checked_at=_now()
            )
        except httpx.HTTPError as e:
            return ProviderHealth(
                provider_id=self.provider_id, status="unreachable", detail=redact_text(str(e)), checked_at=_now()
            )

    def _payload(self, request: LLMRequest, stream: bool) -> dict:
        payload = {
            "model": request.model,
            "messages": [m.model_dump() for m in request.messages],
            "temperature": request.temperature,
            "max_tokens": request.max_output_tokens,
            "stream": stream,
        }
        if request.response_format == "structured_json":
            payload["response_format"] = {"type": "json_object"}
        return payload

    async def complete(
        self, request: LLMRequest, api_key: str | None, base_url: str | None
    ) -> LLMResponse:
        async with self._client() as client:
            r = await client.post(
                f"{self._base(base_url)}/chat/completions",
                headers=self._headers(api_key),
                json=self._payload(request, stream=False),
            )
            _check(r)
            body = r.json()
        content = body["choices"][0]["message"]["content"]
        usage = body.get("usage") or {}
        return LLMResponse(
            request_id=request.request_id,
            provider_id=self.provider_id,
            model=body.get("model", request.model),
            content=content,
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
            prompt_hash=hash_obj([m.model_dump() for m in request.messages]),
            response_hash=hash_obj(content),
        )

    async def stream(
        self, request: LLMRequest, api_key: str | None, base_url: str | None
    ) -> AsyncIterator[LLMChunk]:
        async with self._client() as client:
            async with client.stream(
                "POST",
                f"{self._base(base_url)}/chat/completions",
                headers=self._headers(api_key),
                json=self._payload(request, stream=True),
            ) as r:
                if r.status_code >= 400:
                    detail = (await r.aread())[:400].decode(errors="replace")
                    yield LLMChunk(
                        request_id=request.request_id, done=True,
                        error=redact_text(f"HTTP {r.status_code}: {detail}"),
                    )
                    return
                async for line in r.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        delta = json.loads(data)["choices"][0].get("delta", {}).get("content", "")
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue
                    if delta:
                        yield LLMChunk(request_id=request.request_id, delta=delta)
        yield LLMChunk(request_id=request.request_id, done=True)


def _per_mtok(v) -> float | None:
    try:
        return float(v) * 1_000_000 if v is not None else None
    except (TypeError, ValueError):
        return None


def _check(r: httpx.Response) -> None:
    if len(r.content) > MAX_RESPONSE_BYTES:
        raise ProviderError("Provider response exceeds size cap")
    if r.status_code >= 400:
        raise ProviderError(redact_text(f"HTTP {r.status_code}: {r.text[:300]}"))
