from sim_helpers import make_scenario

from verine.cases.runner import execute_scenario
from verine.optimization.constraints import check_action_set
from verine.optimization.exhaustive import optimize_containment
from verine.simulation.compiler import compile_scenario


def _amap(bundle):
    return {a.action_id: a for a in bundle.actions}


def test_budget_violation_rejected(bundle):
    amap = _amap(bundle)
    feasible, reasons = check_action_set(
        [amap["act_emergency_capacity_purchase"], amap["act_failover_backup_processor"]],
        bundle.default_constraints,
    )
    assert not feasible
    assert any("Budget exceeded" in r for r in reasons)


def test_missing_role_rejected(bundle):
    amap = _amap(bundle)
    feasible, reasons = check_action_set([amap["act_manual_authorization_process"]], bundle.default_constraints)
    assert not feasible
    assert any("unavailable roles" in r for r in reasons)
    assert any("treasury" in r for r in reasons)


def test_unmet_feasibility_fact_rejected(bundle):
    amap = _amap(bundle)
    constraints = bundle.default_constraints.model_copy(update={"facts": []})
    feasible, reasons = check_action_set([amap["act_failover_backup_processor"]], constraints)
    assert not feasible
    assert any("backup_contract_active" in r for r in reasons)


def test_collateral_risk_rejected(bundle):
    amap = _amap(bundle)
    constraints = bundle.default_constraints.model_copy(update={"max_collateral_risk": 0.1})
    feasible, reasons = check_action_set([amap["act_enable_fraud_fallback_rules"]], constraints)
    assert not feasible
    assert any("collateral risk" in r for r in reasons)


def test_deadline_rejected(bundle):
    amap = _amap(bundle)
    constraints = bundle.default_constraints.model_copy(update={"deadline_minutes": 30})
    feasible, reasons = check_action_set([amap["act_failover_backup_processor"]], constraints)
    assert not feasible
    assert any("Deadline exceeded" in r for r in reasons)


def test_optimizer_never_ranks_infeasible_set(bundle):
    inc = bundle.incidents["inc_compound_payment_crisis"]
    scn = make_scenario(bundle)
    compiled = compile_scenario(scn, bundle.snapshot, inc, bundle.actions)
    result = optimize_containment(compiled, bundle.actions)

    assert result["chosen_set"] is not None
    ranked_ids = [result["chosen_set"]["action_ids"]] + [s["action_ids"] for s in result["runner_up_sets"]]
    amap = _amap(bundle)
    for ids in ranked_ids:
        feasible, reasons = check_action_set([amap[i] for i in ids], scn.constraints)
        assert feasible, f"infeasible set ranked: {ids}: {reasons}"
    assert result["rejected_count"] > 0
    assert all(r["reasons"] for r in result["rejected_sets"])


def test_optimizer_beats_no_action_on_compound(bundle):
    inc = bundle.incidents["inc_compound_payment_crisis"]
    scn = make_scenario(bundle)
    compiled = compile_scenario(scn, bundle.snapshot, inc, bundle.actions)
    result = optimize_containment(compiled, bundle.actions)
    chosen = result["chosen_set"]
    base = result["baseline_no_action"]
    assert chosen["expected_service_loss_sl_hours"] < base["expected_service_loss_sl_hours"]
    assert chosen["floor_breach_duration_minutes"] < base["floor_breach_duration_minutes"]
    assert result["improves_on_no_action"] is True


def test_weights_are_visible_and_configurable(bundle):
    inc = bundle.incidents["inc_compound_payment_crisis"]
    scn = make_scenario(bundle)
    compiled = compile_scenario(scn, bundle.snapshot, inc, bundle.actions)
    result = optimize_containment(compiled, bundle.actions)
    assert set(result["weights"]) == {"w_cost", "cost_scale", "w_time", "w_collateral", "w_reversibility"}


def test_no_robust_action_produces_evidence_requests(bundle):
    """When constraints forbid every meaningful action, evidence requests must still rank."""
    inc = bundle.incidents["inc_compound_payment_crisis"]
    constraints = bundle.default_constraints.model_copy(update={"budget": 500, "facts": []})
    scn = make_scenario(bundle, constraints=constraints)
    compiled = compile_scenario(scn, bundle.snapshot, inc, bundle.actions)
    result = execute_scenario(compiled, bundle.actions)
    assert result["case_file"].evidence_requests, "evidence requests must be generated"
    for req in result["case_file"].evidence_requests:
        assert req["estimated_cost_usd"] >= 0
        assert req["estimated_time_minutes"] > 0
        assert req["uncertainty_target"]
