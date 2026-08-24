"""Connector normalization from offline fixtures + SSRF guard (EXP-V001)."""

from pathlib import Path

import pytest

from verine.providers.live.base import ConnectorConfig, RawFetch
from verine.providers.live.registry import live_connector
from verine.providers.llm.openai_compatible import ProviderError, validate_provider_url

FIX = Path(__file__).resolve().parents[2] / "fixtures" / "live"


def _fetch(path: Path) -> RawFetch:
    return RawFetch(content=path.read_bytes(), source_uri=f"fixture://{path.name}",
                    status_code=200, retrieved_at="2026-08-24T12:04:00Z", from_fixture=True)


def test_statuspage_normalization():
    conn = live_connector("statuspage")
    cfg = ConnectorConfig(connector_id="c", connector_type="statuspage", base_url="https://x")
    signals = conn.normalize(_fetch(FIX / "processor_status.json"), cfg)
    assert len(signals) == 1
    s = signals[0]
    assert s.signal_type == "provider_incident"
    assert s.severity == "high"
    assert s.impact_status == "external_signal_only"  # never confirmed internal
    assert "acme payment processor" in s.entities
    assert s.source_event_id == "inc-acme-2026-0824-01"


def test_cisa_delta_and_match_filter():
    conn = live_connector("cisa_kev")
    cfg = ConnectorConfig(connector_id="c", connector_type="cisa_kev",
                          params={"match_terms": ["acme", "payment"]})
    signals = conn.normalize(_fetch(FIX / "cisa_kev.json"), cfg)
    # Only the Acme CVE matches; the unrelated Office Suite CVE is filtered out.
    assert len(signals) == 1
    assert signals[0].source_event_id == "CVE-2026-11111"
    assert signals[0].impact_status == "possible_exposure"


def test_nws_geography_normalization():
    conn = live_connector("nws")
    cfg = ConnectorConfig(connector_id="c", connector_type="nws")
    signals = conn.normalize(_fetch(FIX / "nws_alerts.json"), cfg)
    assert len(signals) == 1
    assert signals[0].signal_type == "weather_alert"
    assert any("new york" in g for g in signals[0].geographies)


def test_schema_drift_fails_loudly():
    conn = live_connector("statuspage")
    cfg = ConnectorConfig(connector_id="c", connector_type="statuspage", base_url="https://x")
    bad = RawFetch(content=b'{"unexpected": true}', source_uri="fixture://bad",
                   status_code=200, retrieved_at="2026-08-24T12:04:00Z", from_fixture=True)
    with pytest.raises(KeyError):
        conn.normalize(bad, cfg)


def test_ssrf_guard_blocks_private_hosts(monkeypatch):
    monkeypatch.setenv("VERINE_ALLOW_PRIVATE_PROVIDER_HOSTS", "0")
    with pytest.raises(ProviderError):
        validate_provider_url("http://127.0.0.1:8080/v1")
    with pytest.raises(ProviderError):
        validate_provider_url("http://169.254.169.254/latest")  # cloud metadata
    # public https is fine
    assert validate_provider_url("https://api.openai.com/v1") == "https://api.openai.com/v1"


def test_ssrf_guard_allows_private_in_local_mode(monkeypatch):
    monkeypatch.setenv("VERINE_ALLOW_PRIVATE_PROVIDER_HOSTS", "1")
    assert validate_provider_url("http://127.0.0.1:11434/v1")
