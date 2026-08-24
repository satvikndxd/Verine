"""Scenario compiler: validate a scenario against its graph, incident, and actions
BEFORE any simulation runs. Invalid scenarios fail here with structured errors."""

from __future__ import annotations

from dataclasses import dataclass

from ..common.errors import ScenarioInvalidError
from ..graph.snapshots import GraphSnapshot
from ..graph.validate import validate_graph
from ..incidents.schema import Incident
from ..optimization.actions import Action
from .scenarios import Scenario


@dataclass
class CompiledScenario:
    scenario: Scenario
    snapshot: GraphSnapshot
    incident: Incident
    actions_by_id: dict[str, Action]
    graph_hash: str
    scenario_hash: str
    warnings: list[str]


def compile_scenario(
    scenario: Scenario,
    snapshot: GraphSnapshot,
    incident: Incident,
    actions: list[Action],
) -> CompiledScenario:
    errors: list[dict] = []
    warnings = validate_graph(snapshot)

    if scenario.graph_snapshot_id != snapshot.graph_snapshot_id:
        errors.append({"field": "graph_snapshot_id", "reason": "Scenario references a different snapshot"})
    if scenario.incident_id != incident.incident_id:
        errors.append({"field": "incident_id", "reason": "Scenario references a different incident"})

    cap = snapshot.capability_map().get(scenario.capability_id)
    if cap is None:
        errors.append({"field": "capability_id", "reason": f"Capability {scenario.capability_id} not in snapshot"})
    elif scenario.constraints.minimum_service_level > cap.target_service_level:
        errors.append(
            {
                "field": "constraints.minimum_service_level",
                "reason": "Minimum service level exceeds capability target",
            }
        )

    node_ids = snapshot.all_node_ids()
    for i, comp in enumerate(incident.components):
        if comp.target_node_id not in node_ids:
            errors.append(
                {"field": f"incident.components[{i}].target_node_id", "reason": f"Unknown node {comp.target_node_id}"}
            )

    edge_ids = {e.edge_id for e in snapshot.edges}
    for hid in scenario.hidden_edge_ids:
        if hid not in edge_ids:
            errors.append({"field": "hidden_edge_ids", "reason": f"Unknown edge {hid}"})

    actions_by_id = {a.action_id: a for a in actions}
    for s in scenario.scheduled_actions:
        a = actions_by_id.get(s.action_id)
        if a is None:
            errors.append({"field": "scheduled_actions", "reason": f"Unknown action {s.action_id}"})
            continue
        for t in a.target_nodes:
            if t not in node_ids:
                errors.append({"field": f"action.{a.action_id}.target_nodes", "reason": f"Unknown node {t}"})
        if s.start_minutes > scenario.horizon_minutes:
            errors.append({"field": "scheduled_actions", "reason": f"{s.action_id} starts after horizon"})

    if scenario.horizon_minutes % scenario.step_minutes != 0:
        errors.append({"field": "horizon_minutes", "reason": "Horizon must be a multiple of step_minutes"})
    if incident.duration_minutes > scenario.horizon_minutes:
        warnings.append("Incident duration exceeds simulation horizon; tail effects will be truncated")

    if errors:
        raise ScenarioInvalidError("Scenario failed compilation", field_errors=errors)

    return CompiledScenario(
        scenario=scenario,
        snapshot=snapshot,
        incident=incident,
        actions_by_id=actions_by_id,
        graph_hash=snapshot.graph_hash(),
        scenario_hash=scenario.scenario_hash(),
        warnings=warnings,
    )
