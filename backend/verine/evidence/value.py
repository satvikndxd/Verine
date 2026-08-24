"""Information-intervention ranker.

When no action set is robust — or uncertainty dominates — the correct output is
an EVIDENCE REQUEST, not a confident recommendation. Ranking is a
decision-analysis heuristic (uncertainty targeted x decision impact / effort),
not a causal value-of-information estimate.
"""

from __future__ import annotations

from ..graph.snapshots import GraphSnapshot

_CATALOG = [
    {
        "trigger": "inferred_edge",
        "request": "Confirm or refute the inferred dependency with the counterparty",
        "cost_usd": 2000,
        "time_minutes": 2880,
        "uncertainty_target": "epistemic",
    },
    {
        "trigger": "undisclosed_dependencies",
        "request": "Obtain a current dependency inventory for the capability",
        "cost_usd": 8000,
        "time_minutes": 10080,
        "uncertainty_target": "epistemic",
    },
    {
        "trigger": "low_observability_affected_node",
        "request": "Add monitoring or request status telemetry for the low-observability node",
        "cost_usd": 4000,
        "time_minutes": 4320,
        "uncertainty_target": "observability",
    },
    {
        "trigger": "recovery_disagreement",
        "request": "Run a failover drill; record backup activation time and throughput",
        "cost_usd": 15000,
        "time_minutes": 2880,
        "uncertainty_target": "model_disagreement",
    },
    {
        "trigger": "lag_disagreement",
        "request": "Measure queue drain rate and dependency lag under load",
        "cost_usd": 5000,
        "time_minutes": 1440,
        "uncertainty_target": "model_disagreement",
    },
]


def rank_evidence_requests(
    snapshot: GraphSnapshot,
    unknowns: list[dict],
    disagreement: dict,
    top_pathway_nodes: list[str],
) -> list[dict]:
    requests: list[dict] = []
    pathway_set = set(top_pathway_nodes)

    def impact_score(subject: str | None) -> float:
        return 1.0 if subject in pathway_set else 0.5

    for u in unknowns:
        for cat in _CATALOG:
            if cat["trigger"] != u["kind"]:
                continue
            subject = u.get("node_id") or u.get("edge_id")
            score = impact_score(_edge_endpoint(snapshot, subject)) * 10000 / (cat["cost_usd"] + cat["time_minutes"])
            requests.append(
                {
                    "request": cat["request"],
                    "subject": subject,
                    "reason": u["detail"],
                    "estimated_cost_usd": cat["cost_usd"],
                    "estimated_time_minutes": cat["time_minutes"],
                    "uncertainty_target": cat["uncertainty_target"],
                    "decision_impact_heuristic": round(score, 6),
                }
            )

    for area in disagreement.get("areas", []):
        if area["normalized_disagreement"] < 0.15:
            continue
        trigger = "recovery_disagreement" if "recovery" in area["metric"] else "lag_disagreement"
        cat = next(c for c in _CATALOG if c["trigger"] == trigger)
        requests.append(
            {
                "request": area["recommended_next_step"],
                "subject": area["metric"],
                "reason": f"Models disagree on {area['metric']} "
                f"(normalized {area['normalized_disagreement']}): {', '.join(area['likely_reasons'])}",
                "estimated_cost_usd": cat["cost_usd"],
                "estimated_time_minutes": cat["time_minutes"],
                "uncertainty_target": cat["uncertainty_target"],
                "decision_impact_heuristic": round(area["normalized_disagreement"], 6),
            }
        )

    requests.sort(key=lambda r: (-r["decision_impact_heuristic"], r["request"]))
    # Dedupe by request text, keep highest-impact instance.
    seen: set[str] = set()
    unique = []
    for r in requests:
        key = f"{r['request']}|{r['subject']}"
        if key not in seen:
            seen.add(key)
            unique.append(r)
    return unique[:10]


def _edge_endpoint(snapshot: GraphSnapshot, subject: str | None) -> str | None:
    if subject is None:
        return None
    for e in snapshot.edges:
        if e.edge_id == subject:
            return e.to_node
    return subject
