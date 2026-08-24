"""Hand-authored expected outputs (fixtures/expected/simple_cases.json) matched exactly."""

import json
from pathlib import Path

import pytest

from verine.capabilities.schema import Capability
from verine.graph.edges import Edge
from verine.graph.nodes import Node
from verine.graph.snapshots import GraphSnapshot
from verine.incidents.schema import Incident
from verine.optimization.actions import Action
from verine.simulation.propagate import run_propagation
from verine.simulation.scenarios import ScheduledAction

EXPECTED = json.loads(
    (Path(__file__).resolve().parents[2] / "fixtures" / "expected" / "simple_cases.json").read_text()
)


def _simple_graph(substitute: bool = False):
    cap = Capability(
        capability_id="cap_t",
        name="T",
        description="d",
        owner_role="ops",
        minimum_service_level=0.5,
        target_service_level=0.99,
        unit="tps",
        criticality="high",
        valid_from="2026-01-01T00:00:00Z",
    )
    nodes = [Node(node_id="node_a", node_type="vendor", name="A", recovery_time_minutes=30)]
    subs = []
    if substitute:
        nodes.append(Node(node_id="node_b", node_type="vendor", name="B", substitutability=1.0))
        subs = ["node_b"]
    edges = [
        Edge(
            edge_id="edge_1",
            from_node="cap_t",
            to_node="node_a",
            edge_type="requires",
            criticality_weight=0.8,
            capacity_fraction=1.0,
            propagation_lag_minutes={"min": 0, "median": 5, "max": 10},
            substitution_options=subs,
        )
    ]
    return GraphSnapshot(graph_snapshot_id="graph_t", capabilities=[cap], nodes=nodes, edges=edges)


def _incident():
    return Incident(
        incident_id="inc_t",
        name="t",
        incident_type="single",
        onset_at="2026-01-01T00:00:00Z",
        duration_minutes=60,
        severity=0.5,
        components=[
            {"target_node_id": "node_a", "mode": "unavailable", "severity": 0.5, "duration_minutes": 60}
        ],
    )


def _series(result, node_id):
    out = {}
    for s in result.steps:
        out[str(s.t_minutes)] = s.node_degradation.get(node_id, 0.0)
    return out


def test_single_edge_case_matches_hand_math():
    exp = EXPECTED["case_single_edge"]
    result = run_propagation(_simple_graph(), _incident(), horizon_minutes=120, step_minutes=5)

    node_series = _series(result, "node_a")
    cap_series = _series(result, "cap_t")
    for t, v in exp["node_a_series"].items():
        assert node_series[t] == pytest.approx(v, abs=1e-6), f"node_a at t={t}"
    for t, v in exp["cap_series"].items():
        assert cap_series[t] == pytest.approx(v, abs=1e-6), f"cap at t={t}"

    m = result.metrics["capabilities"]["cap_t"]
    assert result.metrics["peak_degradation_by_node"]["node_a"] == exp["peak_node_a"]
    assert result.metrics["peak_degradation_by_node"]["cap_t"] == exp["peak_cap"]
    assert m["min_service_level"] == pytest.approx(exp["min_service_level"], abs=1e-6)
    assert m["breached_floor"] is exp["breached_floor"]
    assert m["recovery_time_minutes"] == exp["recovery_time_minutes"]
    assert m["expected_service_loss_sl_hours"] == pytest.approx(exp["expected_service_loss_sl_hours"], abs=1e-4)

    events = {e.target_node_id: e for e in result.impact_events}
    assert events["node_a"].impact_start_minutes == exp["first_impact_node_a"]
    assert events["cap_t"].impact_start_minutes == exp["first_impact_cap"]
    assert events["cap_t"].source_kind == "dependency_edge"
    assert events["cap_t"].via_edge_id == "edge_1"


def test_full_substitute_absorbs_impact():
    exp = EXPECTED["case_full_substitute"]
    result = run_propagation(_simple_graph(substitute=True), _incident(), horizon_minutes=120, step_minutes=5)
    assert result.metrics["peak_degradation_by_node"].get("cap_t", 0.0) == exp["peak_cap"]


def test_action_damping_matches_hand_math():
    exp = EXPECTED["case_action_damping"]
    action = Action(
        action_id="act_damp",
        name="Damp",
        action_type="reroute",
        target_nodes=["node_a"],
        cost=0,
        duration_minutes=0,
        capacity_effect=0.5,
        reversibility=1.0,
        collateral_risk=0.0,
    )
    result = run_propagation(
        _simple_graph(),
        _incident(),
        horizon_minutes=120,
        step_minutes=5,
        scheduled_actions=[ScheduledAction(action_id="act_damp", start_minutes=0)],
        actions_by_id={"act_damp": action},
    )
    assert result.metrics["peak_degradation_by_node"]["node_a"] == exp["peak_node_a"]
    assert result.metrics["peak_degradation_by_node"]["cap_t"] == exp["peak_cap"]
