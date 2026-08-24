"""Containment constraint validation. Infeasible sets are rejected with reasons."""

from __future__ import annotations

from ..simulation.scenarios import ScenarioConstraints
from .actions import Action


def check_action_set(actions: list[Action], constraints: ScenarioConstraints) -> tuple[bool, list[str]]:
    """Return (feasible, rejection_reasons)."""
    reasons: list[str] = []

    total_cost = sum(a.cost for a in actions)
    if total_cost > constraints.budget:
        reasons.append(f"Budget exceeded: cost {total_cost:.0f} > budget {constraints.budget:.0f}")

    if actions:
        slowest = max(a.duration_minutes for a in actions)
        if slowest > constraints.deadline_minutes:
            reasons.append(
                f"Deadline exceeded: slowest action needs {slowest}m > deadline {constraints.deadline_minutes}m"
            )

    available = set(constraints.available_roles)
    for a in actions:
        missing = sorted(set(a.required_roles) - available)
        if missing:
            reasons.append(f"Action {a.action_id} requires unavailable roles: {missing}")

    for a in actions:
        if a.collateral_risk > constraints.max_collateral_risk:
            reasons.append(
                f"Action {a.action_id} collateral risk {a.collateral_risk} > max {constraints.max_collateral_risk}"
            )

    facts = set(constraints.facts)
    for a in actions:
        unmet = sorted(set(a.feasibility_constraints) - facts)
        if unmet:
            reasons.append(f"Action {a.action_id} has unmet feasibility constraints: {unmet}")

    # Mutually conflicting targets: two actions of the same type on the same node.
    seen: dict[tuple[str, str], str] = {}
    for a in actions:
        for t in a.target_nodes:
            key = (a.action_type.value, t)
            if key in seen:
                reasons.append(
                    f"Actions {seen[key]} and {a.action_id} duplicate {a.action_type.value} on {t}"
                )
            seen[key] = a.action_id

    return (len(reasons) == 0, reasons)
