"""Live connector contract and shared fetch machinery.

Rules enforced here for every connector:
- live mode gated by VERINE_LIVE_ENABLED and per-connector `enabled`
- fixture mode (offline) uses the same normalize path as live mode
- timeouts, response-size caps, no redirects, descriptive User-Agent
- ETag / Last-Modified conditional requests via persisted cursors
- schema drift fails loudly (normalize raises), never silently
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

import httpx
from pydantic import BaseModel, ConfigDict, Field

from ...common.errors import VerineError
from ...signals.schema import ExternalSignal

FETCH_TIMEOUT = 20.0


class LiveDisabled(VerineError):
    error_code = "LIVE_DISABLED"


class ConnectorConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    connector_id: str
    connector_type: str
    label: str = ""
    base_url: str | None = None
    params: dict = Field(default_factory=dict)  # adapter-specific (cik, area, match_terms, ...)
    enabled: bool = False
    fixture_path: str | None = None  # offline mode: read this file instead of the network
    poll_interval_seconds: int = Field(default=300, ge=60)
    terms_status: str = "public_api"
    source_strength: str = "strong"  # strong | weak — used by evidence quorum
    source_independence_group: str = ""
    created_at: str = ""


class ConnectorCursor(BaseModel):
    model_config = ConfigDict(extra="forbid")

    connector_id: str
    etag: str | None = None
    last_modified: str | None = None
    last_polled_at: str | None = None
    seen: dict[str, str] = Field(default_factory=dict)  # source_event_id -> normalized_hash
    extra: dict = Field(default_factory=dict)


class RawFetch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: bytes
    source_uri: str
    status_code: int
    headers: dict = Field(default_factory=dict)
    retrieved_at: str
    not_modified: bool = False
    from_fixture: bool = False


class ConnectorHealth(BaseModel):
    model_config = ConfigDict(extra="forbid")

    connector_id: str
    status: str  # live_ok | fixture_ok | live_disabled | error | unreachable
    detail: str = ""
    checked_at: str = ""


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def live_enabled() -> bool:
    return os.environ.get("VERINE_LIVE_ENABLED", "0") == "1"


class BaseLiveConnector:
    connector_type = "base"
    adapter_version = "base@0.1.0"
    signal_type = "advisory"

    def __init__(self, transport: httpx.AsyncBaseTransport | None = None):
        self._transport = transport

    # ------------------------------------------------------------ fetch path
    def endpoint(self, config: ConnectorConfig) -> str:
        raise NotImplementedError

    async def fetch(self, config: ConnectorConfig, cursor: ConnectorCursor) -> RawFetch:
        if config.fixture_path:
            path = Path(config.fixture_path)
            return RawFetch(
                content=path.read_bytes(),
                source_uri=f"fixture://{path.name}",
                status_code=200,
                retrieved_at=now_utc(),
                from_fixture=True,
            )
        if not live_enabled():
            raise LiveDisabled(
                "Live mode is disabled (VERINE_LIVE_ENABLED=0). Configure a fixture_path "
                "for offline mode or enable live mode explicitly."
            )
        if not config.enabled:
            raise LiveDisabled(f"Connector {config.connector_id} is not enabled")

        url = self.endpoint(config)
        headers = {
            "User-Agent": os.environ.get("VERINE_USER_AGENT", "VERINE/0.1 contact@example.com"),
            "Accept": "application/json",
        }
        if cursor.etag:
            headers["If-None-Match"] = cursor.etag
        if cursor.last_modified:
            headers["If-Modified-Since"] = cursor.last_modified
        headers.update(self.extra_headers(config))

        async with httpx.AsyncClient(
            transport=self._transport, timeout=FETCH_TIMEOUT, follow_redirects=False
        ) as client:
            r = await client.get(url, headers=headers)
        if r.status_code == 304:
            return RawFetch(content=b"", source_uri=url, status_code=304,
                            retrieved_at=now_utc(), not_modified=True)
        if r.status_code >= 400:
            raise VerineError(f"Connector {config.connector_id} HTTP {r.status_code}")
        max_bytes = int(os.environ.get("VERINE_MAX_RESPONSE_BYTES", str(50_000_000)))
        if len(r.content) > max_bytes:
            raise VerineError(f"Connector {config.connector_id} response exceeds size cap")
        return RawFetch(
            content=r.content,
            source_uri=url,
            status_code=r.status_code,
            headers={k: v for k, v in r.headers.items() if k.lower() in ("etag", "last-modified", "content-type")},
            retrieved_at=now_utc(),
        )

    def extra_headers(self, config: ConnectorConfig) -> dict:
        return {}

    # -------------------------------------------------------------- normalize
    def normalize(self, raw: RawFetch, config: ConnectorConfig) -> list[ExternalSignal]:
        raise NotImplementedError

    # ----------------------------------------------------------------- health
    async def health(self, config: ConnectorConfig) -> ConnectorHealth:
        try:
            raw = await self.fetch(config, ConnectorCursor(connector_id=config.connector_id))
            signals = self.normalize(raw, config) if not raw.not_modified else []
            mode = "fixture_ok" if raw.from_fixture else "live_ok"
            return ConnectorHealth(
                connector_id=config.connector_id, status=mode,
                detail=f"{len(signals)} signal(s) in latest response", checked_at=now_utc(),
            )
        except LiveDisabled as e:
            return ConnectorHealth(connector_id=config.connector_id, status="live_disabled",
                                   detail=str(e), checked_at=now_utc())
        except httpx.HTTPError as e:
            return ConnectorHealth(connector_id=config.connector_id, status="unreachable",
                                   detail=str(e), checked_at=now_utc())
        except Exception as e:  # schema drift and parse errors stay visible
            return ConnectorHealth(connector_id=config.connector_id, status="error",
                                   detail=f"{type(e).__name__}: {e}", checked_at=now_utc())
