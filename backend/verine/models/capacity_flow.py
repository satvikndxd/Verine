"""Capacity-flow approximation (steady-state bottleneck analysis).

APPROXIMATION, explicitly documented: the capability is treated as a small
static flow network at PEAK incident stress. No lags, no time dynamics.
Each dependency channel constrains deliverable capacity:

    channel_availability = 1 - weight * capacity_fraction * (1 - delivered)
    delivered            = min(1, availability(dependency) + best_redundancy)
    availability(node)   = min(direct_availability, min over channels)

The bottleneck is the argmin channel chain (a min-cut-style explanation on the
explicit synthetic graph). A business is NOT literally a static flow network;
this model exists to disagree informatively with the time-dynamic model.
"""

from __future__ import annotations

from ..common.enums import INCIDENT_MODE_MULTIPLIER
from ..graph.snapshots import GraphSnapshot
from ..incidents.schema import Incident

MODEL_ID = "capacity_flow_v1"


def run_capacity_flow(
    snapshot: GraphSnapshot, incident: Incident, hidden_edge_ids: list[str] | None = None
) -> dict:
    hidden = set(hidden_edge_ids or [])
    node_meta = snapshot.node_map()

    direct_stress: dict[str, float] = {}
    for c in incident.components:
        stress = c.severity * INCIDENT_MODE_MULTIPLIER[c.mode]
        direct_stress[c.target_node_id] = max(direct_stress.get(c.target_node_id, 0.0), stress)

    channels: dict[str, list] = {}
    for e in snapshot.edges:
        if e.edge_id in hidden:
            continue
        channels.setdefault(e.from_node, []).append(e)

    memo: dict[str, float] = {}
    bottleneck_edge: dict[str, str | None] = {}

    def availability(nid: str, stack: tuple = ()) -> float:
        if nid in memo:
            return memo[nid]
        if nid in stack:
            return 1.0  # cycle guard; validator forbids cycles anyway
        avail = 1.0 - direct_stress.get(nid, 0.0)
        worst_edge = None
        for e in sorted(channels.get(nid, []), key=lambda e: e.edge_id):
            dep_avail = availability(e.to_node, stack + (nid,))
            redundancy = 0.0
            for sub in e.substitution_options:
                sub_meta = node_meta.get(sub)
                if sub_meta is None:
                    continue
                sub_avail = availability(sub, stack + (nid,))
                redundancy = max(redundancy, sub_meta.substitutability * sub_avail)
            delivered = min(1.0, dep_avail + redundancy)
            channel_avail = 1.0 - e.criticality_weight * e.capacity_fraction * (1.0 - delivered)
            if channel_avail < avail:
                avail = channel_avail
                worst_edge = e.edge_id
        memo[nid] = round(max(0.0, avail), 6)
        bottleneck_edge[nid] = worst_edge
        return memo[nid]

    results: dict = {"model_id": MODEL_ID, "epistemic_status": "model_result", "capabilities": {}}
    edge_map = {e.edge_id: e for e in snapshot.edges}

    for cap in sorted(snapshot.capabilities, key=lambda c: c.capability_id):
        avail = availability(cap.capability_id)
        max_deg = round(1.0 - avail, 6)

        # Trace bottleneck chain and accumulate median lags for a crude time estimate.
        chain_nodes = [cap.capability_id]
        chain_edges: list[str] = []
        lag_total = 0.0
        cursor = cap.capability_id
        while bottleneck_edge.get(cursor):
            eid = bottleneck_edge[cursor]
            e = edge_map[eid]
            chain_edges.append(eid)
            chain_nodes.append(e.to_node)
            lag_total += e.propagation_lag_minutes.median
            cursor = e.to_node

        floor_deg_needed = 1.0 - (cap.minimum_service_level / cap.target_service_level)
        breaches = max_deg > floor_deg_needed
        recovery_est = None
        if direct_stress:
            comp_end = max(c.onset_offset_minutes + c.duration_minutes for c in incident.components)
            tail = node_meta[cursor].recovery_time_minutes if cursor in node_meta else 0
            recovery_est = comp_end + tail

        results["capabilities"][cap.capability_id] = {
            "steady_state_availability": avail,
            "max_degradation": max_deg,
            "min_service_level": round(cap.target_service_level * avail, 6),
            "breaches_floor": breaches,
            "time_to_floor_minutes": round(lag_total) if breaches else None,
            "recovery_time_minutes": recovery_est,
            "bottleneck_nodes": chain_nodes,
            "bottleneck_edges": chain_edges,
        }

    results["affected_nodes"] = sorted(n for n, a in memo.items() if a < 0.95)
    results["note"] = (
        "Steady-state bottleneck approximation at peak stress; ignores lags and recovery dynamics."
    )
    return results
