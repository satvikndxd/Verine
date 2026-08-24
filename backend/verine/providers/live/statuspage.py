"""Statuspage-compatible adapter (GET {base}/api/v2/incidents/unresolved.json).

A provider's public status is EXTERNAL evidence, never confirmed internal impact."""

from __future__ import annotations

import json

from ...common.hashing import hash_obj
from ...common.ids import derived_id
from ...signals.schema import ExternalSignal
from .base import BaseLiveConnector, ConnectorConfig, RawFetch

_IMPACT_SEVERITY = {"none": "info", "minor": "low", "major": "high", "critical": "critical"}


class StatuspageConnector(BaseLiveConnector):
    connector_type = "statuspage"
    adapter_version = "statuspage@0.1.0"
    signal_type = "provider_incident"

    def endpoint(self, config: ConnectorConfig) -> str:
        if not config.base_url:
            raise ValueError("statuspage connector requires base_url")
        return f"{config.base_url.rstrip('/')}/api/v2/incidents/unresolved.json"

    def normalize(self, raw: RawFetch, config: ConnectorConfig) -> list[ExternalSignal]:
        body = json.loads(raw.content)
        incidents = body["incidents"]  # KeyError = schema drift, fails loudly
        page_name = (body.get("page") or {}).get("name", config.label or config.connector_id)
        signals = []
        for inc in incidents:
            components = [c.get("name", "") for c in inc.get("components", [])]
            entities = [e.lower() for e in ([page_name] + components) if e]
            payload = {
                "id": inc["id"], "status": inc.get("status"), "impact": inc.get("impact"),
                "updated_at": inc.get("updated_at"), "components": components,
            }
            signals.append(
                ExternalSignal(
                    signal_id=derived_id("signal", {"c": config.connector_id, "e": inc["id"], "h": hash_obj(payload)}),
                    provider_id=config.connector_id,
                    connector_type=self.connector_type,
                    source_uri=raw.source_uri,
                    source_event_id=inc["id"],
                    signal_type="provider_incident",
                    title=inc.get("name", "Provider incident"),
                    summary=f"Status: {inc.get('status', 'unknown')}; impact: {inc.get('impact', 'unknown')}; "
                            f"components: {', '.join(components) or 'unspecified'}",
                    published_at=inc.get("created_at") or raw.retrieved_at,
                    updated_at=inc.get("updated_at"),
                    retrieved_at=raw.retrieved_at,
                    valid_from=inc.get("started_at") or inc.get("created_at"),
                    severity=_IMPACT_SEVERITY.get(inc.get("impact", ""), "medium"),
                    entities=sorted(set(entities)),
                    normalized_hash=hash_obj(payload),
                    parser_version=self.adapter_version,
                )
            )
        return signals
