"""Capability mapping: external signals -> declared incident components.

Only OPERATIONAL signal types (provider_incident, weather_alert) become
incident components for simulation. Vulnerability/filing/advisory signals stay
context with impact_status possible_exposure/external_signal_only — they are
never simulated as degradation without user confirmation.

Severity and duration are DECLARED MODEL INPUTS with intervals, labeled
inferred; they are not measurements."""

from __future__ import annotations

from ..signals.schema import ExternalSignal

SEVERITY_VALUE = {"info": 0.1, "low": 0.3, "medium": 0.45, "high": 0.6, "critical": 0.8}

OPERATIONAL_TYPES = {"provider_incident", "provider_maintenance", "weather_alert"}

DEFAULT_DURATION_MIN = 120
ASSUMPTIONS = [
    "Signal severity words map to declared numeric severities (info 0.1 … critical 0.8).",
    "Unresolved external incidents are assigned a 120-minute assumed duration with a 30-360m interval.",
    "Latency wording maps to mode=latency; otherwise capacity_reduction.",
    "Weather alerts stress the mapped geography node only; overlap is not confirmed impact.",
]


def build_incident_components(
    signals: list[ExternalSignal],
    matches_by_signal: dict[str, list[dict]],
) -> tuple[list[dict], list[dict]]:
    """Return (components, context_signals). Components target matched nodes."""
    components: list[dict] = []
    context: list[dict] = []
    seen_targets: dict[str, float] = {}

    for s in signals:
        matches = matches_by_signal.get(s.signal_id, [])
        if s.signal_type not in OPERATIONAL_TYPES or not matches:
            context.append({
                "signal_id": s.signal_id,
                "signal_type": s.signal_type,
                "impact_status": s.impact_status,
                "reason": ("no node match" if not matches else "non-operational signal type"),
            })
            continue
        sev = SEVERITY_VALUE.get(s.severity, 0.45)
        mode = "latency" if "latenc" in (s.title + s.summary).lower() else "capacity_reduction"
        for m in matches:
            target = m["node_id"]
            if seen_targets.get(target, 0) >= sev:
                continue  # keep the strongest component per node
            seen_targets[target] = sev
            components = [c for c in components if c["target_node_id"] != target]
            components.append({
                "target_node_id": target,
                "mode": mode,
                "severity": sev,
                "severity_interval": {"low": max(0.0, sev - 0.15), "median": sev,
                                      "high": min(1.0, sev + 0.15)},
                "duration_minutes": DEFAULT_DURATION_MIN,
                "duration_interval_minutes": {"low": 30, "median": DEFAULT_DURATION_MIN, "high": 360},
                "evidence_status": "inferred",
            })
    components.sort(key=lambda c: c["target_node_id"])
    return components, context
