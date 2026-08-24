"""Direct reachability baseline (B2 baseline).

Answers only: which nodes CAN be affected, ignoring weights, lags, capacity,
and redundancy. Reverse-reachability from incident target nodes over
dependency edges.
"""

from __future__ import annotations

from ..graph.snapshots import GraphSnapshot
from ..incidents.schema import Incident

MODEL_ID = "reachability_v1"


def run_reachability(
    snapshot: GraphSnapshot, incident: Incident, hidden_edge_ids: list[str] | None = None
) -> dict:
    hidden = set(hidden_edge_ids or [])
    # edge from_node depends on to_node => degradation of to_node reaches from_node
    dependents: dict[str, list[str]] = {}
    for e in snapshot.edges:
        if e.edge_id in hidden:
            continue
        dependents.setdefault(e.to_node, []).append(e.from_node)

    frontier = sorted({c.target_node_id for c in incident.components})
    reached: set[str] = set(frontier)
    while frontier:
        nxt: list[str] = []
        for n in frontier:
            for d in sorted(dependents.get(n, [])):
                if d not in reached:
                    reached.add(d)
                    nxt.append(d)
        frontier = sorted(nxt)

    cap_ids = {c.capability_id for c in snapshot.capabilities}
    return {
        "model_id": MODEL_ID,
        "epistemic_status": "model_result",
        "affected_nodes": sorted(reached),
        "affected_capabilities": sorted(reached & cap_ids),
        "note": "Upper bound on blast radius; ignores weights, lags, capacity, and redundancy.",
    }
