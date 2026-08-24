"""Deterministic propagation model — thin wrapper binding the engine to a compiled scenario."""

from __future__ import annotations

from ..simulation.compiler import CompiledScenario
from ..simulation.propagate import run_propagation
from ..simulation.state import PropagationResult

MODEL_ID = "deterministic_propagation_v1"


def run_deterministic(compiled: CompiledScenario, record_steps: bool = True) -> PropagationResult:
    scn = compiled.scenario
    return run_propagation(
        compiled.snapshot,
        compiled.incident,
        horizon_minutes=scn.horizon_minutes,
        step_minutes=scn.step_minutes,
        hidden_edge_ids=scn.hidden_edge_ids,
        scheduled_actions=scn.scheduled_actions,
        actions_by_id=compiled.actions_by_id,
        model_id=MODEL_ID,
        seed=scn.seed,
        record_steps=record_steps,
    )
