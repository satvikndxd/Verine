"""Greedy fallback for large action libraries: add the single feasible action
with the best marginal utility until no improvement or max size reached."""

from __future__ import annotations

from ..simulation.compiler import CompiledScenario
from .actions import Action
from .constraints import check_action_set


def greedy_containment(
    compiled: CompiledScenario,
    actions: list[Action],
    weights,
    max_set_size: int,
) -> tuple[list[dict], list[dict]]:
    from .exhaustive import _evaluate_set

    evaluated: list[dict] = []
    rejected: list[dict] = []
    current: list[Action] = []
    current_eval = _evaluate_set(compiled, current, weights)

    for _ in range(max_set_size):
        best_gain = 0.0
        best_action = None
        best_eval = None
        for a in actions:
            if a in current:
                continue
            cand = current + [a]
            feasible, reasons = check_action_set(cand, compiled.scenario.constraints)
            if not feasible:
                rejected.append({"action_ids": sorted(x.action_id for x in cand), "reasons": reasons})
                continue
            ev = _evaluate_set(compiled, cand, weights)
            gain = ev["utility"] - current_eval["utility"]
            if gain > best_gain + 1e-9:
                best_gain, best_action, best_eval = gain, a, ev
        if best_action is None:
            break
        current.append(best_action)
        current_eval = best_eval
        evaluated.append(best_eval)

    return evaluated, rejected
