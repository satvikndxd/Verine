"""Deterministic discrete-time propagation engine (5-minute steps by default).

SIMULATION SEMANTICS (documented rules, not real-world causal estimates):

1. Incident components impose a direct degradation on their target node while
   active:  direct = severity * mode_multiplier.  After the component window
   ends, the direct effect decays linearly over the node's
   `recovery_time_minutes`.
2. Dependency edges point dependent -> dependency. Impact flows in reverse:
   for edge j -> i (j depends on i),
       impact_to_j = criticality_weight
                     * delayed_degradation_of_i
                     * capacity_fraction
                     * (1 - effective_redundancy)
   where delayed degradation is read from the source node's history at
   (t - lag_median), never earlier than one step back (effective minimum lag
   is one simulation step).
3. effective_redundancy = max over substitution options s of
       substitutability(s) * (1 - degradation(s))
   using the substitute's previous-step degradation.
4. Node degradation combines by MAX (not sum): the worst channel dominates.
   This keeps behavior monotone: adding an incident can never reduce damage.
5. Scheduled actions become effective at (start + action.duration). Once
   effective, each action multiplies its targets' degradation by
   (1 - capacity_effect). Multiple actions compose multiplicatively.
6. Capability service level = target_service_level * (1 - capability degradation).
7. Hidden edges (incomplete-topology mode) are EXCLUDED from propagation; the
   unknowns detector reports the induced observability risk separately.

All outputs carry epistemic_status "model_result"/"simulated".
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..common.enums import INCIDENT_MODE_MULTIPLIER
from ..graph.snapshots import GraphSnapshot
from ..incidents.schema import Incident
from ..optimization.actions import Action
from .scenarios import ScheduledAction
from .state import ImpactEvent, Pathway, PropagationResult, StepState

ASSUMPTIONS = [
    {
        "assumption_id": "asm_max_combination_v1",
        "statement": "Concurrent impact channels combine by max, not sum.",
        "epistemic_status": "hypothesis",
    },
    {
        "assumption_id": "asm_linear_recovery_v1",
        "statement": "Nodes recover linearly over recovery_time_minutes after incident end.",
        "epistemic_status": "hypothesis",
    },
    {
        "assumption_id": "asm_capacity_linear_v1",
        "statement": "Edge impact scales linearly with criticality_weight and capacity_fraction.",
        "epistemic_status": "hypothesis",
    },
    {
        "assumption_id": "asm_median_lag_v1",
        "statement": "Deterministic model uses the median of each edge's declared lag interval.",
        "epistemic_status": "hypothesis",
    },
]

DEGRADATION_THRESHOLD = 0.05
_ROUND = 6


@dataclass
class ParamOverrides:
    """Monte Carlo sampling hooks. Keys are indices/ids from the declared fixture."""

    component_severity: dict[int, float] = field(default_factory=dict)
    component_duration: dict[int, int] = field(default_factory=dict)
    edge_lag_minutes: dict[str, float] = field(default_factory=dict)
    node_recovery_minutes: dict[str, float] = field(default_factory=dict)


def run_propagation(
    snapshot: GraphSnapshot,
    incident: Incident,
    *,
    horizon_minutes: int,
    step_minutes: int = 5,
    hidden_edge_ids: list[str] | None = None,
    scheduled_actions: list[ScheduledAction] | None = None,
    actions_by_id: dict[str, Action] | None = None,
    overrides: ParamOverrides | None = None,
    model_id: str = "deterministic_propagation_v1",
    seed: int = 0,
    record_steps: bool = True,
) -> PropagationResult:
    hidden = set(hidden_edge_ids or [])
    scheduled = scheduled_actions or []
    actions_by_id = actions_by_id or {}
    ov = overrides or ParamOverrides()

    node_meta = snapshot.node_map()
    cap_meta = snapshot.capability_map()
    all_ids = sorted(snapshot.all_node_ids())

    def recovery_minutes(node_id: str) -> float:
        if node_id in ov.node_recovery_minutes:
            return ov.node_recovery_minutes[node_id]
        n = node_meta.get(node_id)
        return float(n.recovery_time_minutes) if n else 30.0

    # Incoming impact channels per dependent node (reverse of edge direction).
    channels: dict[str, list] = {nid: [] for nid in all_ids}
    for e in snapshot.edges:
        if e.edge_id in hidden:
            continue
        lag = ov.edge_lag_minutes.get(e.edge_id, e.propagation_lag_minutes.median)
        channels[e.from_node].append((e, lag))
    for nid in channels:
        channels[nid].sort(key=lambda item: item[0].edge_id)

    # Incident component windows.
    comps = []
    for idx, c in enumerate(incident.components):
        sev = ov.component_severity.get(idx, c.severity)
        dur = ov.component_duration.get(idx, c.duration_minutes)
        comps.append(
            {
                "idx": idx,
                "target": c.target_node_id,
                "mode": c.mode,
                "severity": sev,
                "start": c.onset_offset_minutes,
                "end": c.onset_offset_minutes + dur,
            }
        )

    # Action effectiveness times.
    effective_at: list[tuple[int, Action]] = []
    for s in scheduled:
        a = actions_by_id.get(s.action_id)
        if a is None:
            raise ValueError(f"Scheduled action {s.action_id} has no definition")
        effective_at.append((s.start_minutes + a.duration_minutes, a))
    effective_at.sort(key=lambda x: (x[0], x[1].action_id))

    n_steps = horizon_minutes // step_minutes + 1
    history: dict[str, list[float]] = {nid: [0.0] for nid in all_ids}
    steps: list[StepState] = []
    first_impact: dict[str, int] = {}
    last_impact: dict[str, int] = {}
    peak: dict[str, float] = {}
    attribution: dict[str, tuple[str, str, str | None]] = {}  # node -> (kind, source, edge_id)

    # Topological order so same-step direct effects propagate consistently
    # (channels still read delayed history, see delayed_value below).
    order = _topo_order(all_ids, snapshot, hidden)

    def delayed_value(nid: str, t: int, lag: float, current_step: int) -> float:
        src_step = min(current_step - 1, int((t - lag) // step_minutes))
        if src_step < 0:
            return 0.0
        h = history[nid]
        return h[src_step] if src_step < len(h) else h[-1]

    for step_idx in range(n_steps):
        t = step_idx * step_minutes
        active_nodes: list[str] = []
        eff_actions = [a for (eff_t, a) in effective_at if eff_t <= t]
        deg_now: dict[str, float] = {}

        for nid in order:
            # 1) direct incident effect with linear recovery tail
            direct = 0.0
            for c in comps:
                if c["target"] != nid:
                    continue
                base = c["severity"] * INCIDENT_MODE_MULTIPLIER[c["mode"]]
                if c["start"] <= t < c["end"]:
                    val = base
                    if nid not in active_nodes:
                        active_nodes.append(nid)
                elif t >= c["end"]:
                    rec = recovery_minutes(nid)
                    val = base * max(0.0, 1.0 - (t - c["end"]) / rec) if rec > 0 else 0.0
                else:
                    val = 0.0
                if val > direct:
                    direct = val
                    if val > DEGRADATION_THRESHOLD:
                        attribution.setdefault(nid, ("incident", f"component_{c['idx']}", None))

            # 2) propagated impact over dependency channels
            best_prop = 0.0
            best_edge = None
            for e, lag in channels[nid]:
                src = e.to_node
                src_deg = delayed_value(src, t, lag, step_idx)
                if src_deg <= 0.0:
                    continue
                redundancy = 0.0
                for sub in e.substitution_options:
                    sub_meta = node_meta.get(sub)
                    if sub_meta is None:
                        continue
                    sub_deg = history[sub][step_idx - 1] if step_idx > 0 else 0.0
                    redundancy = max(redundancy, sub_meta.substitutability * (1.0 - sub_deg))
                impact = e.criticality_weight * src_deg * e.capacity_fraction * (1.0 - redundancy)
                if impact > best_prop:
                    best_prop = impact
                    best_edge = e

            raw = max(direct, best_prop)
            if best_prop > direct and best_edge is not None and raw > DEGRADATION_THRESHOLD:
                attribution.setdefault(nid, ("dependency_edge", best_edge.to_node, best_edge.edge_id))

            # 3) effective actions damp degradation multiplicatively
            for a in eff_actions:
                if nid in a.target_nodes:
                    raw *= 1.0 - a.capacity_effect

            deg = round(min(1.0, max(0.0, raw)), _ROUND)
            deg_now[nid] = deg
            if deg > DEGRADATION_THRESHOLD:
                first_impact.setdefault(nid, t)
                last_impact[nid] = t
                peak[nid] = max(peak.get(nid, 0.0), deg)

        for nid in all_ids:
            history[nid].append(deg_now[nid])

        service_levels = {
            cid: round(cap.target_service_level * (1.0 - deg_now[cid]), _ROUND)
            for cid, cap in cap_meta.items()
        }
        if record_steps:
            steps.append(
                StepState(
                    t_minutes=t,
                    service_levels=service_levels,
                    node_degradation={k: v for k, v in sorted(deg_now.items()) if v > 0.0},
                    active_incident_nodes=sorted(active_nodes),
                    effective_actions=sorted(a.action_id for a in eff_actions),
                )
            )

    impact_events = _build_impact_events(first_impact, last_impact, peak, attribution, model_id, horizon_minutes)
    pathways = _trace_pathways(snapshot, hidden, first_impact, peak, cap_meta, model_id)
    metrics = _compute_metrics(history, cap_meta, snapshot, step_minutes, horizon_minutes, first_impact, peak)

    return PropagationResult(
        model_id=model_id,
        seed=seed,
        steps=steps,
        impact_events=impact_events,
        pathways=pathways,
        metrics=metrics,
        assumptions=ASSUMPTIONS,
    )


def _topo_order(all_ids: list[str], snapshot: GraphSnapshot, hidden: set[str]) -> list[str]:
    """Order nodes dependencies-first (edge from_node depends on to_node)."""
    adj: dict[str, list[str]] = {nid: [] for nid in all_ids}
    indeg: dict[str, int] = {nid: 0 for nid in all_ids}
    for e in snapshot.edges:
        if e.edge_id in hidden:
            continue
        # to_node (dependency) must be computed before from_node (dependent)
        adj[e.to_node].append(e.from_node)
        indeg[e.from_node] += 1
    queue = sorted([n for n, d in indeg.items() if d == 0])
    order: list[str] = []
    while queue:
        n = queue.pop(0)
        order.append(n)
        for m in sorted(adj[n]):
            indeg[m] -= 1
            if indeg[m] == 0:
                queue.append(m)
        queue.sort()
    if len(order) < len(all_ids):  # cycle fallback: deterministic sorted order
        rest = sorted(set(all_ids) - set(order))
        order.extend(rest)
    return order


def _build_impact_events(first_impact, last_impact, peak, attribution, model_id, horizon) -> list[ImpactEvent]:
    events = []
    for i, nid in enumerate(sorted(first_impact, key=lambda n: (first_impact[n], n))):
        kind, source, edge_id = attribution.get(nid, ("incident", "unknown", None))
        end = last_impact.get(nid)
        events.append(
            ImpactEvent(
                impact_event_id=f"impact_{i:03d}_{nid}",
                source_node_id=source,
                source_kind=kind,
                via_edge_id=edge_id,
                target_node_id=nid,
                impact_start_minutes=first_impact[nid],
                impact_end_minutes=end if end is not None and end < horizon else None,
                magnitude=round(peak.get(nid, 0.0), _ROUND),
                rule="impact = weight * delayed_source_degradation * capacity_fraction * (1 - redundancy); channels combine by max",
                model_id=model_id,
                assumption_ids=[a["assumption_id"] for a in ASSUMPTIONS],
            )
        )
    return events


def _trace_pathways(snapshot, hidden, first_impact, peak, cap_meta, model_id) -> list[Pathway]:
    """Enumerate simple dependency paths from each capability to impacted leaf sources."""
    edges_by_dependent: dict[str, list] = {}
    for e in snapshot.edges:
        if e.edge_id in hidden:
            continue
        edges_by_dependent.setdefault(e.from_node, []).append(e)

    pathways: list[Pathway] = []

    def walk(node: str, node_chain: list[str], edge_chain: list[str], strength: float, depth: int) -> None:
        if depth > 8:
            return
        out = sorted(edges_by_dependent.get(node, []), key=lambda e: e.edge_id)
        extended = False
        for e in out:
            if e.to_node in node_chain:
                continue
            if e.to_node in first_impact and peak.get(e.to_node, 0) > DEGRADATION_THRESHOLD:
                extended = True
                walk(
                    e.to_node,
                    node_chain + [e.to_node],
                    edge_chain + [e.edge_id],
                    strength * e.criticality_weight * e.capacity_fraction,
                    depth + 1,
                )
        if not extended and len(node_chain) > 1:
            pathways.append(
                Pathway(
                    pathway_id=f"path_{len(pathways):03d}",
                    node_chain=node_chain,
                    edge_chain=edge_chain,
                    strength=round(strength, _ROUND),
                    first_impact_minutes=first_impact.get(node_chain[-1], 0),
                    description=" -> ".join(node_chain),
                )
            )

    for cid in sorted(cap_meta):
        if cid in first_impact:
            walk(cid, [cid], [], 1.0, 0)

    pathways.sort(key=lambda p: (-p.strength, p.pathway_id))
    for i, p in enumerate(pathways):
        p.pathway_id = f"path_{i:03d}"
    return pathways[:10]


def _compute_metrics(history, cap_meta, snapshot, step_minutes, horizon, first_impact, peak) -> dict:
    metrics: dict = {"capabilities": {}}
    for cid, cap in sorted(cap_meta.items()):
        h = history[cid][1:]  # skip initial state
        sls = [cap.target_service_level * (1.0 - d) for d in h]
        min_sl = min(sls) if sls else cap.target_service_level
        time_to_floor = None
        recovery_at = None
        breach_minutes = 0
        for i, sl in enumerate(sls):
            t = i * step_minutes
            if sl < cap.minimum_service_level:
                breach_minutes += step_minutes
                if time_to_floor is None:
                    time_to_floor = t
            if sl < cap.target_service_level - 1e-9:
                recovery_at = t + step_minutes
        loss = sum(max(0.0, cap.target_service_level - sl) for sl in sls) * step_minutes / 60.0
        metrics["capabilities"][cid] = {
            "min_service_level": round(min_sl, _ROUND),
            "max_degradation": round(max(h) if h else 0.0, _ROUND),
            "time_to_floor_minutes": time_to_floor,
            "breached_floor": time_to_floor is not None,
            "floor_breach_duration_minutes": breach_minutes,
            "recovery_time_minutes": recovery_at,
            "expected_service_loss_sl_hours": round(loss, _ROUND),
        }
    metrics["affected_nodes"] = sorted(n for n in first_impact if peak.get(n, 0) > DEGRADATION_THRESHOLD)
    metrics["affected_node_count"] = len(metrics["affected_nodes"])
    metrics["peak_degradation_by_node"] = {n: round(v, _ROUND) for n, v in sorted(peak.items())}
    metrics["horizon_minutes"] = horizon
    metrics["step_minutes"] = step_minutes
    return metrics
