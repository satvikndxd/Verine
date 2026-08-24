"""Containment optimization.

Exhaustive enumeration of action subsets (size <= max_set_size) for small
action libraries, greedy fallback for large ones. The objective is a
TRANSPARENT, user-visible weighted utility:

    utility(A) = - expected_service_loss(A)
                 - w_cost * action_cost(A) / cost_scale
                 - w_time * time_to_effect(A) / 60
                 - w_collateral * collateral_risk(A)
                 + w_reversibility * mean_reversibility(A)

There is no hidden "optimal" action. All weights ship in the response.
Results are SIMULATED outcomes over the fixture graph, not causal claims.
"""

from __future__ import annotations

from itertools import combinations

from pydantic import BaseModel, ConfigDict, Field

from ..simulation.compiler import CompiledScenario
from ..simulation.propagate import run_propagation
from ..simulation.scenarios import ScheduledAction
from .actions import Action
from .constraints import check_action_set

EXHAUSTIVE_LIMIT = 12  # actions; above this, greedy fallback engages


class OptimizerWeights(BaseModel):
    model_config = ConfigDict(extra="forbid")
    w_cost: float = Field(default=0.2, ge=0)
    cost_scale: float = Field(default=100_000, gt=0)
    w_time: float = Field(default=0.05, ge=0)
    w_collateral: float = Field(default=0.3, ge=0)
    w_reversibility: float = Field(default=0.1, ge=0)


def _evaluate_set(
    compiled: CompiledScenario, action_set: list[Action], weights: OptimizerWeights
) -> dict:
    scn = compiled.scenario
    scheduled = [ScheduledAction(action_id=a.action_id, start_minutes=0) for a in action_set]
    result = run_propagation(
        compiled.snapshot,
        compiled.incident,
        horizon_minutes=scn.horizon_minutes,
        step_minutes=scn.step_minutes,
        hidden_edge_ids=scn.hidden_edge_ids,
        scheduled_actions=scheduled,
        actions_by_id={a.action_id: a for a in action_set},
        model_id="deterministic_propagation_v1",
        seed=scn.seed,
        record_steps=False,
    )
    cm = result.metrics["capabilities"][scn.capability_id]
    cost = sum(a.cost for a in action_set)
    time_to_effect = max((a.duration_minutes for a in action_set), default=0)
    collateral = max((a.collateral_risk for a in action_set), default=0.0)
    reversibility = (
        sum(a.reversibility for a in action_set) / len(action_set) if action_set else 1.0
    )
    utility = (
        -cm["expected_service_loss_sl_hours"]
        - weights.w_cost * cost / weights.cost_scale
        - weights.w_time * time_to_effect / 60.0
        - weights.w_collateral * collateral
        + weights.w_reversibility * reversibility
    )
    return {
        "action_ids": sorted(a.action_id for a in action_set),
        "utility": round(utility, 6),
        "expected_service_loss_sl_hours": cm["expected_service_loss_sl_hours"],
        "min_service_level": cm["min_service_level"],
        "breaches_floor": cm["breached_floor"],
        "floor_breach_duration_minutes": cm["floor_breach_duration_minutes"],
        "time_to_floor_minutes": cm["time_to_floor_minutes"],
        "recovery_time_minutes": cm["recovery_time_minutes"],
        "total_cost": cost,
        "time_to_effect_minutes": time_to_effect,
        "max_collateral_risk": collateral,
        "mean_reversibility": round(reversibility, 6),
        "epistemic_status": "simulated",
    }


def optimize_containment(
    compiled: CompiledScenario,
    actions: list[Action],
    weights: OptimizerWeights | None = None,
    max_set_size: int = 3,
) -> dict:
    weights = weights or OptimizerWeights()
    constraints = compiled.scenario.constraints
    actions = sorted(actions, key=lambda a: a.action_id)

    method = "exhaustive" if len(actions) <= EXHAUSTIVE_LIMIT else "greedy"
    evaluated: list[dict] = []
    rejected: list[dict] = []

    baseline = _evaluate_set(compiled, [], weights)
    baseline["label"] = "no_action_baseline"

    if method == "exhaustive":
        candidates: list[list[Action]] = []
        for size in range(1, max_set_size + 1):
            candidates.extend(list(c) for c in combinations(actions, size))
        for cand in candidates:
            feasible, reasons = check_action_set(cand, constraints)
            if not feasible:
                rejected.append({"action_ids": sorted(a.action_id for a in cand), "reasons": reasons})
                continue
            evaluated.append(_evaluate_set(compiled, cand, weights))
    else:
        from .greedy import greedy_containment

        evaluated, rejected = greedy_containment(compiled, actions, weights, max_set_size)

    evaluated.sort(key=lambda e: (-e["utility"], e["action_ids"]))
    chosen = evaluated[0] if evaluated else None
    robust = chosen is not None and chosen["utility"] > baseline["utility"] + 1e-9

    return {
        "method": method,
        "weights": weights.model_dump(),
        "baseline_no_action": baseline,
        "chosen_set": chosen,
        "runner_up_sets": evaluated[1:4],
        "rejected_sets": rejected[:20],
        "rejected_count": len(rejected),
        "evaluated_count": len(evaluated),
        "improves_on_no_action": robust,
        "epistemic_status": "simulated",
        "disclaimer": "Simulated outcomes on a synthetic fixture graph; not causal effect estimates.",
    }
