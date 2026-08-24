"""NOAA/NWS active alerts adapter (https://api.weather.gov/alerts/active).

Geographic overlap NEVER implies confirmed business impact — signals map to
configured geography nodes as external hazard context only."""

from __future__ import annotations

import json

from ...common.hashing import hash_obj
from ...common.ids import derived_id
from ...signals.schema import ExternalSignal
from .base import BaseLiveConnector, ConnectorConfig, RawFetch

NWS_URL = "https://api.weather.gov/alerts/active"

_NWS_SEVERITY = {"extreme": "critical", "severe": "high", "moderate": "medium", "minor": "low"}


class NwsConnector(BaseLiveConnector):
    connector_type = "nws"
    adapter_version = "nws@0.1.0"
    signal_type = "weather_alert"

    def endpoint(self, config: ConnectorConfig) -> str:
        base = config.base_url or NWS_URL
        area = config.params.get("area")
        point = config.params.get("point")
        if area:
            return f"{base}?area={area}"
        if point:
            return f"{base}?point={point}"
        return base

    def extra_headers(self, config: ConnectorConfig) -> dict:
        return {"Accept": "application/geo+json"}

    def normalize(self, raw: RawFetch, config: ConnectorConfig) -> list[ExternalSignal]:
        body = json.loads(raw.content)
        features = body["features"]  # schema drift fails loudly
        signals = []
        for f in features:
            p = f["properties"]
            event_id = f.get("id", p.get("id", ""))
            payload = {"id": event_id, "event": p.get("event"), "sent": p.get("sent"),
                       "severity": p.get("severity"), "areaDesc": p.get("areaDesc")}
            signals.append(
                ExternalSignal(
                    signal_id=derived_id("signal", {"c": config.connector_id, "e": event_id, "h": hash_obj(payload)}),
                    provider_id=config.connector_id,
                    connector_type=self.connector_type,
                    source_uri=raw.source_uri,
                    source_event_id=event_id,
                    signal_type="weather_alert",
                    title=p.get("headline") or p.get("event", "Weather alert"),
                    summary=f"{p.get('event', '')} — {p.get('areaDesc', '')}. "
                            "Geographic overlap does not imply confirmed business impact.",
                    event_at=p.get("onset") or p.get("effective"),
                    published_at=p.get("sent") or raw.retrieved_at,
                    updated_at=p.get("effective"),
                    retrieved_at=raw.retrieved_at,
                    valid_from=p.get("effective"),
                    valid_to=p.get("expires"),
                    severity=_NWS_SEVERITY.get(str(p.get("severity", "")).lower(), "medium"),
                    geographies=[g.strip().lower() for g in str(p.get("areaDesc", "")).split(";") if g.strip()],
                    normalized_hash=hash_obj(payload),
                    parser_version=self.adapter_version,
                )
            )
        return signals
