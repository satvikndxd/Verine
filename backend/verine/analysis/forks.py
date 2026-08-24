"""Counterfactual containment forks: immutable, replayable branches of a case.

A fork = parent case + action set (+ constraint overrides) re-simulated with the
same seed and models. Forks never execute anything; `require_reversible_actions`
rejects low-reversibility actions up front."""

from __future__ import annotations

from ..common.ids import derived_id
from ..optimization.constraints import check_action_set
from ..simulation.scenarios import ScenarioConstraints, ScheduledAction

ACTION_CLASSES = [
    "failover", "degrade_optional_feature", "reroute", "isolate_dependency",
    "increase_observability", "contact_provider", "gather_evidence", "wait_and_monitor",
]

REVERSIBILITY_FLOOR = 0.5


def build_fork(
    svc,  # VerineService
    parent_case_doc: dict,
    action_ids: list[str],
    constraints_override: dict | None,
    created_at: str,
) -> dict:
    parent_case = parent_case_doc["case_json"]
    parent_scenario = svc.get_scenario(parent_case_doc["scenario_id"])

    actions_by_id = {a.action_id: a for a in svc.list_actions()}
    chosen = [actions_by_id[a] for a in action_ids if a in actions_by_id]
    missing = sorted(set(action_ids) - set(a.action_id for a in chosen))
    if missing:
        raise ValueError(f"Unknown actions: {missing}")

    require_reversible = bool((constraints_override or {}).get("require_reversible_actions"))
    if constraints_override:
        base = {k: v for k, v in constraints_override.items() if k != "require_reversible_actions"}
        constraints = ScenarioConstraints(**base)
    else:
        constraints = parent_scenario.constraints

    feasibility_reasons: list[str] = []
    if chosen:
        feasible, feasibility_reasons = check_action_set(chosen, constraints)
    else:
        feasible = True  # no-action fork is always comparable

    if require_reversible:
        for a in chosen:
            if a.reversibility < REVERSIBILITY_FLOOR:
                feasible = False
                feasibility_reasons.append(
                    f"Action {a.action_id} reversibility {a.reversibility} < {REVERSIBILITY_FLOOR} "
                    "(require_reversible_actions)"
                )

    fork_id = derived_id("fork", {
        "parent": parent_case["case_file_id"], "actions": sorted(action_ids),
        "constraints": constraints.model_dump(mode="json"),
    })

    if not feasible:
        return {
            "fork_id": fork_id,
            "parent_case_id": parent_case["case_file_id"],
            "action_ids": sorted(action_ids),
            "status": "infeasible",
            "feasibility_reasons": feasibility_reasons,
            "created_at": created_at,
            "epistemic_status": "simulated",
        }

    scenario, compiled = svc.compile_and_store_scenario(
        capability_id=parent_scenario.capability_id,
        incident_id=parent_scenario.incident_id,
        graph_snapshot_id=parent_scenario.graph_snapshot_id,
        constraints=ScenarioConstraints(**{k: v for k, v in constraints.model_dump().items()}),
        hidden_edge_ids=parent_scenario.hidden_edge_ids,
        scheduled_actions=[ScheduledAction(action_id=a, start_minutes=0) for a in sorted(action_ids)],
        seed=parent_scenario.seed,
        horizon_minutes=parent_scenario.horizon_minutes,
        monte_carlo_replications=parent_scenario.monte_carlo_replications,
        model_set=parent_scenario.model_set,
    )
    result = svc.run_simulation(scenario.scenario_id)
    cap_id = parent_scenario.capability_id
    det = result["model_outputs"]["deterministic_propagation_v1"]["metrics"]["capabilities"][cap_id]

    return {
        "fork_id": fork_id,
        "parent_case_id": parent_case["case_file_id"],
        "parent_run_hash": parent_case["run_hash"],
        "action_ids": sorted(action_ids),
        "constraints": constraints.model_dump(mode="json"),
        "scenario_id": scenario.scenario_id,
        "case_file_id": result["case_file"]["case_file_id"],
        "run_hash": result["run_hash"],
        "seed": parent_scenario.seed,
        "model_set": sorted(parent_scenario.model_set),
        "status": "simulated",
        "metrics": {
            "min_service_level": det["min_service_level"],
            "breached_floor": det["breached_floor"],
            "floor_breach_duration_minutes": det["floor_breach_duration_minutes"],
            "recovery_time_minutes": det["recovery_time_minutes"],
            "expected_service_loss_sl_hours": det["expected_service_loss_sl_hours"],
            "total_cost": sum(a.cost for a in chosen),
        },
        "created_at": created_at,
        "epistemic_status": "simulated",
    }
