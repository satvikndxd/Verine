"""Robustness evaluator: re-evaluate a chosen action set under multiple declared
incident severity multipliers. A decision-analysis heuristic, not a causal claim."""

from __future__ import annotations

from ..incidents.schema import Incident
from ..simulation.compiler import CompiledScenario
from .actions import Action

SEVERITY_MULTIPLIERS = [0.75, 1.0, 1.25]


def evaluate_robustness(compiled: CompiledScenario, action_set: list[Action]) -> dict:
    from .exhaustive import OptimizerWeights, _evaluate_set

    weights = OptimizerWeights()
    rows = []
    original = compiled.incident
    for mult in SEVERITY_MULTIPLIERS:
        scaled = Incident(
            **{
                **original.model_dump(),
                "components": [
                    {**c.model_dump(), "severity": min(1.0, round(c.severity * mult, 6))}
                    for c in original.components
                ],
            }
        )
        compiled.incident = scaled
        try:
            with_actions = _evaluate_set(compiled, action_set, weights)
            without = _evaluate_set(compiled, [], weights)
        finally:
            compiled.incident = original
        rows.append(
            {
                "severity_multiplier": mult,
                "loss_with_actions": with_actions["expected_service_loss_sl_hours"],
                "loss_without_actions": without["expected_service_loss_sl_hours"],
                "still_breaches_floor": with_actions["breaches_floor"],
            }
        )
    helps_everywhere = all(r["loss_with_actions"] <= r["loss_without_actions"] + 1e-9 for r in rows)
    return {
        "action_ids": sorted(a.action_id for a in action_set),
        "rows": rows,
        "robust_across_declared_severities": helps_everywhere,
        "epistemic_status": "simulated",
    }
