"""CISA Known Exploited Vulnerabilities adapter.

Emits deltas for KEV entries matching configured match_terms. Without a
connected asset inventory a KEV match means `possible_exposure`, never
`confirmed_exposure`."""

from __future__ import annotations

import json

from ...common.hashing import hash_obj
from ...common.ids import derived_id
from ...signals.schema import ExternalSignal
from .base import BaseLiveConnector, ConnectorConfig, RawFetch

KEV_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"


class CisaKevConnector(BaseLiveConnector):
    connector_type = "cisa_kev"
    adapter_version = "cisa_kev@0.1.0"
    signal_type = "vulnerability_kev"

    def endpoint(self, config: ConnectorConfig) -> str:
        return config.base_url or KEV_URL

    def normalize(self, raw: RawFetch, config: ConnectorConfig) -> list[ExternalSignal]:
        body = json.loads(raw.content)
        vulns = body["vulnerabilities"]  # schema drift fails loudly
        match_terms = [t.lower() for t in config.params.get("match_terms", [])]
        signals = []
        for v in vulns:
            haystack = " ".join(
                str(v.get(k, "")) for k in ("vendorProject", "product", "vulnerabilityName")
            ).lower()
            if match_terms and not any(t in haystack for t in match_terms):
                continue
            payload = {"cve": v["cveID"], "dateAdded": v.get("dateAdded"), "action": v.get("requiredAction")}
            signals.append(
                ExternalSignal(
                    signal_id=derived_id("signal", {"c": config.connector_id, "e": v["cveID"], "h": hash_obj(payload)}),
                    provider_id=config.connector_id,
                    connector_type=self.connector_type,
                    source_uri=raw.source_uri,
                    source_event_id=v["cveID"],
                    signal_type="vulnerability_kev",
                    title=f"{v['cveID']}: {v.get('vulnerabilityName', 'KEV entry')}",
                    summary=f"Vendor: {v.get('vendorProject')}; product: {v.get('product')}; "
                            f"required action: {v.get('requiredAction', 'n/a')}. "
                            "KEV match implies POSSIBLE exposure only; no asset inventory is connected.",
                    published_at=(v.get("dateAdded") or raw.retrieved_at[:10]) + "T00:00:00Z"
                    if "T" not in str(v.get("dateAdded", "")) else v["dateAdded"],
                    retrieved_at=raw.retrieved_at,
                    severity="high",
                    entities=sorted({str(v.get("vendorProject", "")).lower(), str(v.get("product", "")).lower()} - {""}),
                    normalized_hash=hash_obj(payload),
                    impact_status="possible_exposure",
                    parser_version=self.adapter_version,
                )
            )
        return signals
