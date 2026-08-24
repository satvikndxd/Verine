"""SEC EDGAR submissions adapter (https://data.sec.gov/submissions/CIK{cik}.json).

Preserves accession number, filing date, form type, and as-filed provenance.
Requires a descriptive SEC_USER_AGENT per fair-access rules."""

from __future__ import annotations

import json
import os

from ...common.hashing import hash_obj
from ...common.ids import derived_id
from ...signals.schema import ExternalSignal
from .base import BaseLiveConnector, ConnectorConfig, RawFetch

DEFAULT_FORMS = ["8-K", "10-Q", "10-K", "6-K"]


class SecConnector(BaseLiveConnector):
    connector_type = "sec_edgar"
    adapter_version = "sec_edgar@0.1.0"
    signal_type = "regulatory_filing"

    def endpoint(self, config: ConnectorConfig) -> str:
        cik = str(config.params.get("cik", "")).zfill(10)
        if not cik.strip("0"):
            raise ValueError("sec_edgar connector requires params.cik")
        base = config.base_url or "https://data.sec.gov"
        return f"{base.rstrip('/')}/submissions/CIK{cik}.json"

    def extra_headers(self, config: ConnectorConfig) -> dict:
        ua = os.environ.get("SEC_USER_AGENT") or os.environ.get(
            "VERINE_USER_AGENT", "VERINE/0.1 contact@example.com"
        )
        return {"User-Agent": ua}

    def normalize(self, raw: RawFetch, config: ConnectorConfig) -> list[ExternalSignal]:
        body = json.loads(raw.content)
        recent = body["filings"]["recent"]  # schema drift fails loudly
        company = body.get("name", config.label or "issuer")
        watch_forms = set(config.params.get("forms", DEFAULT_FORMS))
        limit = int(config.params.get("max_filings", 20))
        signals = []
        for i in range(min(limit, len(recent.get("accessionNumber", [])))):
            form = recent["form"][i]
            if watch_forms and form not in watch_forms:
                continue
            accession = recent["accessionNumber"][i]
            filing_date = recent["filingDate"][i]
            payload = {"accession": accession, "form": form, "filingDate": filing_date}
            signals.append(
                ExternalSignal(
                    signal_id=derived_id("signal", {"c": config.connector_id, "e": accession, "h": hash_obj(payload)}),
                    provider_id=config.connector_id,
                    connector_type=self.connector_type,
                    source_uri=raw.source_uri,
                    source_event_id=accession,
                    signal_type="regulatory_filing",
                    title=f"{company}: {form} filed {filing_date}",
                    summary=f"Form {form}, accession {accession}, as-filed. "
                            f"Primary doc: {recent.get('primaryDocument', [''] * (i + 1))[i]}",
                    published_at=f"{filing_date}T00:00:00Z",
                    retrieved_at=raw.retrieved_at,
                    severity="info" if form not in ("8-K",) else "medium",
                    entities=[company.lower()],
                    normalized_hash=hash_obj(payload),
                    parser_version=self.adapter_version,
                )
            )
        return signals
