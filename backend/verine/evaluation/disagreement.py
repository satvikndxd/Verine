"""Model disagreement report. Disagreement is preserved and explained, never averaged away."""

from __future__ import annotations

from .metrics import normalized_diff

_REASON_HINTS = {
    "max_degradation": (
        ["max-vs-min channel combination", "redundancy delivery assumption"],
        ["failover test evidence", "measured substitute capacity"],
        "run a failover drill and record substitute throughput",
    ),
    "time_to_floor_minutes": (
        ["propagation lag uncertainty", "steady-state model ignores lags"],
        ["measured dependency lag under load"],
        "measure queue drain rate and dependency lag under load",
    ),
    "recovery_time_minutes": (
        ["recovery-time uncertainty", "backup capacity assumption"],
        ["backup provider SLA", "regional failover test result"],
        "obtain failover test evidence and backup activation SLA",
    ),
    "affected_node_set": (
        ["reachability ignores weights and redundancy", "hidden/inferred edges"],
        ["current dependency inventory", "confirmation of inferred edges"],
        "confirm or refute inferred dependencies with the vendor",
    ),
}


def build_disagreement_report(comparables: list[dict], horizon_minutes: int) -> dict:
    areas: list[dict] = []
    quantified = [c for c in comparables if c.get("max_degradation") is not None]

    for metric, scale in [
        ("max_degradation", 1.0),
        ("time_to_floor_minutes", float(horizon_minutes)),
        ("recovery_time_minutes", float(horizon_minutes)),
    ]:
        vals = {c["model_id"]: c.get(metric) for c in quantified}
        if len(vals) < 2:
            continue
        pairs = list(vals.values())
        max_diff = 0.0
        for i in range(len(pairs)):
            for j in range(i + 1, len(pairs)):
                d = normalized_diff(pairs[i], pairs[j], scale)
                if d is not None:
                    max_diff = max(max_diff, d)
        hints = _REASON_HINTS[metric]
        areas.append(
            {
                "metric": metric,
                "models": vals,
                "normalized_disagreement": round(max_diff, 6),
                "likely_reasons": hints[0],
                "missing_evidence": hints[1],
                "recommended_next_step": hints[2],
            }
        )

    # Affected-node set disagreement (Jaccard distance across all models).
    sets = {c["model_id"]: set(c.get("affected_nodes") or []) for c in comparables}
    if len(sets) >= 2:
        ids = sorted(sets)
        max_jaccard_dist = 0.0
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                a, b = sets[ids[i]], sets[ids[j]]
                union = a | b
                dist = 1.0 - (len(a & b) / len(union)) if union else 0.0
                max_jaccard_dist = max(max_jaccard_dist, dist)
        hints = _REASON_HINTS["affected_node_set"]
        areas.append(
            {
                "metric": "affected_node_set",
                "models": {mid: sorted(s) for mid, s in sets.items()},
                "normalized_disagreement": round(max_jaccard_dist, 6),
                "likely_reasons": hints[0],
                "missing_evidence": hints[1],
                "recommended_next_step": hints[2],
            }
        )

    worst = max((a["normalized_disagreement"] for a in areas), default=0.0)
    level = "minor" if worst < 0.10 else "moderate" if worst < 0.25 else "material"
    return {
        "overall_level": level,
        "overall_disagreement": round(worst, 6),
        "areas": areas,
        "interpretation": (
            "Disagreement between models signals missing dependencies, uncertain capacity, "
            "or an assumption conflict — it is preserved, not averaged away."
        ),
    }
