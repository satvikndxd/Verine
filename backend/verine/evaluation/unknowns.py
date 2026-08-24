"""Unknown/observability risk detector.

Hidden edges (incomplete-topology mode), inferred edges, low-confidence edges,
and low-observability nodes must INCREASE reported uncertainty — they never
silently disappear.
"""

from __future__ import annotations

from ..common.uncertainty import Interval, Uncertainty
from ..graph.snapshots import GraphSnapshot


def detect_unknowns(
    snapshot: GraphSnapshot,
    hidden_edge_ids: list[str],
    affected_nodes: list[str],
    disagreement_overall: float,
) -> dict:
    hidden = set(hidden_edge_ids)
    affected = set(affected_nodes)

    unknowns: list[dict] = []
    if hidden:
        unknowns.append(
            {
                "kind": "undisclosed_dependencies",
                "detail": f"{len(hidden)} declared dependencies are hidden from models in this scenario "
                "(incomplete-topology mode). The blast radius may be underestimated.",
                "count": len(hidden),
                "epistemic_status": "unknown",
            }
        )
    for e in snapshot.edges:
        if e.edge_id in hidden:
            continue
        if e.epistemic_status.value in ("inferred", "hypothesis", "unknown"):
            unknowns.append(
                {
                    "kind": "inferred_edge",
                    "detail": f"Edge {e.edge_id} ({e.from_node} -> {e.to_node}) is {e.epistemic_status.value} "
                    f"with confidence {e.confidence}. It is NOT a confirmed dependency.",
                    "edge_id": e.edge_id,
                    "confidence": e.confidence,
                    "epistemic_status": e.epistemic_status.value,
                }
            )
        elif e.confidence < 0.7:
            unknowns.append(
                {
                    "kind": "low_confidence_edge",
                    "detail": f"Edge {e.edge_id} has confidence {e.confidence}",
                    "edge_id": e.edge_id,
                    "confidence": e.confidence,
                    "epistemic_status": e.epistemic_status.value,
                }
            )
    for n in snapshot.nodes:
        if n.observability < 0.6 and n.node_id in affected:
            unknowns.append(
                {
                    "kind": "low_observability_affected_node",
                    "detail": f"Affected node {n.node_id} has observability {n.observability}; "
                    "its true state may differ from the model.",
                    "node_id": n.node_id,
                    "observability": n.observability,
                    "epistemic_status": "unknown",
                }
            )

    n_edges = max(1, len(snapshot.edges))
    hidden_frac = len(hidden) / n_edges
    inferred_frac = sum(
        1 for e in snapshot.edges if e.edge_id not in hidden and e.epistemic_status.value != "observed"
    ) / n_edges
    obs_scores = [n.observability for n in snapshot.nodes if n.node_id in affected]
    observability = round(sum(obs_scores) / len(obs_scores), 6) if obs_scores else 1.0
    epistemic = round(min(1.0, 0.15 + 0.9 * hidden_frac + 0.6 * inferred_frac), 6)

    uncertainty = Uncertainty(
        aleatoric=0.2,
        epistemic=epistemic,
        observability=observability,
        model_disagreement=round(min(1.0, disagreement_overall), 6),
        interval=Interval(low=0.0, median=epistemic, high=min(1.0, epistemic + hidden_frac)),
        explanation=(
            f"{len(hidden)} hidden edge(s), inferred-edge fraction {inferred_frac:.2f}, "
            f"mean observability of affected nodes {observability:.2f}."
        ),
    )
    return {
        "unknowns": unknowns,
        "uncertainty": uncertainty.model_dump(mode="json"),
        "reliability_label": uncertainty.reliability_label(),
    }
