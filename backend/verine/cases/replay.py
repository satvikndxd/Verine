"""Replay a Resilience Case File byte-for-byte and compare hashes."""

from __future__ import annotations

from ..optimization.actions import Action
from ..simulation.compiler import CompiledScenario, compile_scenario
from .runner import execute_scenario
from .schema import CaseFile


def replay_case(
    case: CaseFile,
    compiled: CompiledScenario,
    actions: list[Action],
) -> dict:
    if compiled.scenario_hash != case.scenario_hash:
        return {
            "replayed": False,
            "reason": "Scenario hash mismatch: stored scenario differs from case file",
            "expected_scenario_hash": case.scenario_hash,
            "actual_scenario_hash": compiled.scenario_hash,
        }
    if compiled.graph_hash != case.graph_hash:
        return {
            "replayed": False,
            "reason": "Graph hash mismatch: stored snapshot differs from case file",
            "expected_graph_hash": case.graph_hash,
            "actual_graph_hash": compiled.graph_hash,
        }
    result = execute_scenario(compiled, actions, executed_at=case.executed_at)
    match = result["run_hash"] == case.run_hash
    return {
        "replayed": True,
        "hashes_match": match,
        "expected_run_hash": case.run_hash,
        "actual_run_hash": result["run_hash"],
        "graph_hash": compiled.graph_hash,
        "scenario_hash": compiled.scenario_hash,
        "metrics_match": result["case_file"].metrics == case.metrics,
    }
