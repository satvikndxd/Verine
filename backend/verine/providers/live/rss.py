"""Allowlisted RSS/Atom adapter for official advisories.

- Exact URLs or allowlisted domains only.
- Feed content is UNTRUSTED TEXT: it is stored and displayed as data; nothing
  in it is ever executed or interpreted as instructions.
- Parsed with xml.etree (no DTD/external-entity resolution in ElementTree).
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from urllib.parse import urlparse

from ...common.hashing import hash_obj
from ...common.ids import derived_id
from ...signals.schema import ExternalSignal
from .base import BaseLiveConnector, ConnectorConfig, RawFetch

_ATOM = "{http://www.w3.org/2005/Atom}"
MAX_ITEMS = 50
MAX_TEXT = 2000


class RssConnector(BaseLiveConnector):
    connector_type = "rss"
    adapter_version = "rss@0.1.0"
    signal_type = "advisory"

    def endpoint(self, config: ConnectorConfig) -> str:
        url = config.base_url
        if not url:
            raise ValueError("rss connector requires base_url")
        allow = config.params.get("allowlist_domains", [])
        host = urlparse(url).hostname or ""
        if allow and not any(host == d or host.endswith("." + d) for d in allow):
            raise ValueError(f"Feed host {host!r} is not in the allowlist")
        return url

    @staticmethod
    def _text(el, limit: int = MAX_TEXT) -> str:
        return ((el.text or "").strip()[:limit]) if el is not None else ""

    def normalize(self, raw: RawFetch, config: ConnectorConfig) -> list[ExternalSignal]:
        root = ET.fromstring(raw.content)
        items: list[dict] = []
        if root.tag == f"{_ATOM}feed":
            for entry in root.findall(f"{_ATOM}entry")[:MAX_ITEMS]:
                link = entry.find(f"{_ATOM}link")
                items.append({
                    "id": self._text(entry.find(f"{_ATOM}id")) or self._text(entry.find(f"{_ATOM}title")),
                    "title": self._text(entry.find(f"{_ATOM}title")),
                    "summary": self._text(entry.find(f"{_ATOM}summary")),
                    "published": self._text(entry.find(f"{_ATOM}published"))
                    or self._text(entry.find(f"{_ATOM}updated")),
                    "link": link.get("href", "") if link is not None else "",
                })
        else:  # RSS 2.0
            for item in root.findall("./channel/item")[:MAX_ITEMS]:
                items.append({
                    "id": self._text(item.find("guid")) or self._text(item.find("link")),
                    "title": self._text(item.find("title")),
                    "summary": self._text(item.find("description")),
                    "published": self._text(item.find("pubDate")),
                    "link": self._text(item.find("link")),
                })
        signals = []
        for it in items:
            if not it["id"]:
                continue
            payload = {"id": it["id"], "title": it["title"], "published": it["published"]}
            signals.append(
                ExternalSignal(
                    signal_id=derived_id("signal", {"c": config.connector_id, "e": it["id"], "h": hash_obj(payload)}),
                    provider_id=config.connector_id,
                    connector_type=self.connector_type,
                    source_uri=raw.source_uri,
                    source_event_id=it["id"],
                    signal_type="advisory",
                    title=it["title"] or "Advisory",
                    summary=it["summary"],
                    published_at=it["published"] or raw.retrieved_at,
                    retrieved_at=raw.retrieved_at,
                    severity="info",
                    entities=[t.lower() for t in config.params.get("entity_hints", [])],
                    normalized_hash=hash_obj(payload),
                    parser_version=self.adapter_version,
                )
            )
        return signals
