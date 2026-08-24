"""NVD CVE API 2.0 adapter (https://services.nvd.nist.gov/rest/json/cves/2.0).

Backend-only optional API key (NVD_API_KEY); keyword/date-window queries."""

from __future__ import annotations

import json
import os
from urllib.parse import urlencode

from ...common.hashing import hash_obj
from ...common.ids import derived_id
from ...signals.schema import ExternalSignal
from .base import BaseLiveConnector, ConnectorConfig, RawFetch

NVD_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"


class NvdConnector(BaseLiveConnector):
    connector_type = "nvd"
    adapter_version = "nvd@0.1.0"
    signal_type = "vulnerability_cve"

    def endpoint(self, config: ConnectorConfig) -> str:
        base = config.base_url or NVD_URL
        query = {}
        if config.params.get("keyword"):
            query["keywordSearch"] = config.params["keyword"]
        if config.params.get("last_mod_start"):
            query["lastModStartDate"] = config.params["last_mod_start"]
        if config.params.get("last_mod_end"):
            query["lastModEndDate"] = config.params["last_mod_end"]
        query["resultsPerPage"] = str(min(int(config.params.get("results_per_page", 50)), 200))
        return f"{base}?{urlencode(query)}"

    def extra_headers(self, config: ConnectorConfig) -> dict:
        key = os.environ.get("NVD_API_KEY", "")
        return {"apiKey": key} if key else {}

    def normalize(self, raw: RawFetch, config: ConnectorConfig) -> list[ExternalSignal]:
        body = json.loads(raw.content)
        items = body["vulnerabilities"]  # schema drift fails loudly
        signals = []
        for item in items:
            cve = item["cve"]
            cve_id = cve["id"]
            descriptions = cve.get("descriptions", [])
            desc = next((d["value"] for d in descriptions if d.get("lang") == "en"), "")
            metrics = cve.get("metrics", {})
            score = None
            for key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
                if metrics.get(key):
                    score = metrics[key][0].get("cvssData", {}).get("baseScore")
                    break
            severity = ("critical" if score and score >= 9 else "high" if score and score >= 7
                        else "medium" if score and score >= 4 else "low")
            payload = {"cve": cve_id, "lastModified": cve.get("lastModified"), "score": score}
            signals.append(
                ExternalSignal(
                    signal_id=derived_id("signal", {"c": config.connector_id, "e": cve_id, "h": hash_obj(payload)}),
                    provider_id=config.connector_id,
                    connector_type=self.connector_type,
                    source_uri=raw.source_uri,
                    source_event_id=cve_id,
                    signal_type="vulnerability_cve",
                    title=f"{cve_id} (CVSS {score if score is not None else 'n/a'})",
                    summary=(desc[:400] + ("…" if len(desc) > 400 else "")) +
                            " CVE context implies POSSIBLE exposure only; no asset inventory is connected.",
                    published_at=cve.get("published") or raw.retrieved_at,
                    updated_at=cve.get("lastModified"),
                    retrieved_at=raw.retrieved_at,
                    severity=severity,
                    entities=[t.lower() for t in config.params.get("entity_hints", [])],
                    normalized_hash=hash_obj(payload),
                    impact_status="possible_exposure",
                    parser_version=self.adapter_version,
                )
            )
        return signals
