"""Simulation invariants (N066): monotonicity, replay determinism, unknown handling."""

import copy

from sim_helpers import make_scenario

from verine.cases.runner import execute_scenario
from verine.graph.snapshots import GraphSnapshot
from verine.incidents.schema import Incident
from verine.models.deterministic import run_deterministic
from verine.simulation.compiler import compile_scenario

CAP = "cap_digital_payments_authorization"


def _loss(result):
    return result.metrics["capabilities"][CAP]["expected_service_loss_sl_hours"]


def _run(bundle, incident, **scn_kw):
    scn = make_scenario(bundle, incident_id=incident.incident_id, **scn_kw)
    compiled = compile_scenario(scn, bundle.snapshot, incident, bundle.actions)
    return run_deterministic(compiled)


def test_removing_incident_component_never_increases_damage(bundle):
    """Degradation is monotone in the incident: dropping a component cannot worsen loss."""
    full = bundle.incidents["inc_compound_payment_crisis"]
    full_result = _run(bundle, full)
    for drop_idx in range(len(full.components)):
        remaining = [c for i, c in enumerate(full.components) if i != drop_idx]
        sub = Incident(
            **{
                **full.model_dump(),
                "incident_type": "compound" if len(remaining) > 1 else "single",
                "components": [c.model_dump() for c in remaining],
            }
        )
        sub_result = _run(bundle, sub)
        assert _loss(sub_result) <= _loss(full_result) + 1e-9
        assert set(sub_result.metrics["affected_nodes"]) <= set(full_result.metrics["affected_nodes"])


def test_actions_never_increase_damage(bundle):
    """Any scheduled action (pure damping) cannot worsen the outcome."""
    inc = bundle.incidents["inc_compound_payment_crisis"]
    no_action = _run(bundle, inc)
    for action in bundle.actions:
        with_action = _run(
            bundle,
            inc,
            scheduled_actions=[{"action_id": action.action_id, "start_minutes": 0}],
        )
        assert _loss(with_action) <= _loss(no_action) + 1e-9, action.action_id


def test_increasing_redundancy_never_worsens_outcome(bundle):
    """Raising a substitute's substitutability cannot increase expected loss."""
    inc = bundle.incidents["inc_compound_payment_crisis"]
    base = _run(bundle, inc)

    boosted_nodes = []
    for n in bundle.snapshot.nodes:
        n2 = copy.deepcopy(n)
        if n.node_id == "node_backup_processor":
            n2.substitutability = min(1.0, n.substitutability + 0.3)
        boosted_nodes.append(n2)
    boosted_snapshot = GraphSnapshot(
        graph_snapshot_id=bundle.snapshot.graph_snapshot_id,
        capabilities=bundle.snapshot.capabilities,
        nodes=boosted_nodes,
        edges=bundle.snapshot.edges,
    )
    scn = make_scenario(bundle)
    compiled = compile_scenario(scn, boosted_snapshot, inc, bundle.actions)
    boosted = run_deterministic(compiled)
    assert _loss(boosted) <= _loss(base) + 1e-9


def test_degradation_never_improves_without_action_or_recovery(bundle):
    """While all incident components are active and no actions run, capability
    service level is non-increasing."""
    inc = bundle.incidents["inc_compound_payment_crisis"]
    result = _run(bundle, inc)
    active_until = min(c.onset_offset_minutes + c.duration_minutes for c in inc.components)
    prev = None
    for s in result.steps:
        if s.t_minutes >= active_until:
            break
        sl = s.service_levels[CAP]
        if prev is not None:
            assert sl <= prev + 1e-9, f"service level improved at t={s.t_minutes} without action/recovery"
        prev = sl


def test_replay_hash_identical(bundle, compiled_compound):
    r1 = execute_scenario(compiled_compound, bundle.actions)
    r2 = execute_scenario(compiled_compound, bundle.actions)
    assert r1["run_hash"] == r2["run_hash"]
    assert r1["case_file"].metrics == r2["case_file"].metrics


def test_hidden_edges_increase_uncertainty_not_silently_dropped(bundle):
    inc = bundle.incidents["inc_compound_payment_crisis"]
    scn_full = make_scenario(bundle, model_set=["deterministic_propagation_v1", "capacity_flow_v1"])
    scn_hidden = make_scenario(
        bundle,
        model_set=["deterministic_propagation_v1", "capacity_flow_v1"],
        hidden_edge_ids=["edge_idp_region", "edge_backup_region"],
    )
    full = execute_scenario(compile_scenario(scn_full, bundle.snapshot, inc, bundle.actions), bundle.actions)
    hidden = execute_scenario(compile_scenario(scn_hidden, bundle.snapshot, inc, bundle.actions), bundle.actions)

    u_full = full["unknowns"]["uncertainty"]["epistemic"]
    u_hidden = hidden["unknowns"]["uncertainty"]["epistemic"]
    assert u_hidden > u_full, "hidden edges must increase epistemic uncertainty"
    kinds = {u["kind"] for u in hidden["unknowns"]["unknowns"]}
    assert "undisclosed_dependencies" in kinds


def test_model_disagreement_nonempty_for_compound_case(bundle, compiled_compound):
    result = execute_scenario(compiled_compound, bundle.actions)
    report = result["disagreement"]
    assert report["areas"], "designated ambiguous case must produce disagreement areas"
    for area in report["areas"]:
        assert area["likely_reasons"], "disagreement must be explained"
        assert area["recommended_next_step"]
