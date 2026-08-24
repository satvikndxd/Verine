"""Scenario runner: executes the declared model set, builds the disagreement
report, unknowns, containment ranking, evidence requests, and the Resilience
Case File. Fully deterministic for a fixed compiled scenario."""

from __future__ import annotations

from ..common.hashing import hash_obj
from ..common.ids import derived_id
from ..evaluation.compare import extract_comparable
from ..evaluation.disagreement import build_disagreement_report
from ..evaluation.unknowns import detect_unknowns
from ..evidence.value import rank_evidence_requests
from ..models.capacity_flow import run_capacity_flow
from ..models.deterministic import run_deterministic
from ..models.monte_carlo import run_monte_carlo
from ..models.reachability import run_reachability
from ..optimization.actions import Action
from ..optimization.exhaustive import OptimizerWeights, optimize_containment
from ..simulation.compiler import CompiledScenario
from .schema import CaseFile


def execute_scenario(
    compiled: CompiledScenario,
    actions: list[Action],
    weights: OptimizerWeights | None = None,
    executed_at: str = "1970-01-01T00:00:00Z",
) -> dict:
    scn = compiled.scenario
    outputs: dict[str, object] = {}

    for model_id in scn.model_set:
        if model_id == "reachability_v1":
            outputs[model_id] = run_reachability(compiled.snapshot, compiled.incident, scn.hidden_edge_ids)
        elif model_id == "deterministic_propagation_v1":
            outputs[model_id] = run_deterministic(compiled)
        elif model_id == "capacity_flow_v1":
            outputs[model_id] = run_capacity_flow(compiled.snapshot, compiled.incident, scn.hidden_edge_ids)
        elif model_id == "monte_carlo_v1":
            outputs[model_id] = run_monte_carlo(compiled)

    comparables = [extract_comparable(o, scn.capability_id) for o in outputs.values()]
    disagreement = build_disagreement_report(comparables, scn.horizon_minutes)

    det = outputs.get("deterministic_propagation_v1")
    affected = det.metrics["affected_nodes"] if det is not None else []
    unknown_report = detect_unknowns(
        compiled.snapshot, scn.hidden_edge_ids, affected, disagreement["overall_disagreement"]
    )

    containment = optimize_containment(compiled, actions, weights)

    pathway_nodes: list[str] = []
    top_pathways: list[dict] = []
    if det is not None:
        top_pathways = [p.model_dump(mode="json") for p in det.pathways[:5]]
        for p in det.pathways[:3]:
            pathway_nodes.extend(p.node_chain)

    evidence_requests = rank_evidence_requests(
        compiled.snapshot, unknown_report["unknowns"], disagreement, pathway_nodes
    )

    serialized_outputs = {
        mid: (o.model_dump(mode="json") if hasattr(o, "model_dump") else o) for mid, o in outputs.items()
    }
    run_manifest = {
        "graph_hash": compiled.graph_hash,
        "scenario_hash": compiled.scenario_hash,
        "seed": scn.seed,
        "model_set": sorted(scn.model_set),
        "model_outputs": serialized_outputs,
    }
    run_hash = hash_obj(run_manifest)

    cap_metrics = det.metrics["capabilities"][scn.capability_id] if det is not None else {}
    breached = bool(cap_metrics.get("breached_floor"))
    chosen = containment.get("chosen_set")
    baseline_loss = containment["baseline_no_action"]["expected_service_loss_sl_hours"]
    chosen_loss = chosen["expected_service_loss_sl_hours"] if chosen else baseline_loss
    material_improvement = baseline_loss > 0 and (baseline_loss - chosen_loss) / baseline_loss >= 0.20
    if not cap_metrics.get("max_degradation"):
        status = "no_material_impact"
    elif breached:
        if chosen and not chosen.get("breaches_floor", True):
            status = "floor_breach_prevented_by_containment"
        elif chosen and material_improvement:
            status = "transient_floor_breach_containment_partial"
        else:
            status = "floor_breached_containment_uncertain"
    else:
        status = "degraded_but_contained"

    case_file_id = derived_id("case", {"scenario_hash": compiled.scenario_hash, "run_hash": run_hash})
    case = CaseFile(
        case_file_id=case_file_id,
        scenario_id=scn.scenario_id,
        graph_hash=compiled.graph_hash,
        scenario_hash=compiled.scenario_hash,
        run_hash=run_hash,
        model_versions=sorted(scn.model_set),
        seed=scn.seed,
        executed_at=executed_at,
        capability_status=status,
        impact_timeline=[e.model_dump(mode="json") for e in (det.impact_events if det else [])],
        blast_radius={
            "affected_nodes": affected,
            "affected_node_count": len(affected),
            "peak_degradation_by_node": det.metrics["peak_degradation_by_node"] if det else {},
        },
        top_pathways=top_pathways,
        containment_sets=[
            s
            for s in [containment.get("chosen_set")] + containment.get("runner_up_sets", [])
            if s is not None
        ],
        model_disagreement=disagreement,
        evidence_requests=evidence_requests,
        unknowns=unknown_report["unknowns"],
        assumptions=(det.assumptions if det else []),
        metrics={"deterministic": cap_metrics, "uncertainty": unknown_report["uncertainty"]},
        replay_command=f"verine case replay {case_file_id}",
    )

    return {
        "model_outputs": serialized_outputs,
        "comparables": comparables,
        "disagreement": disagreement,
        "unknowns": unknown_report,
        "containment": containment,
        "run_hash": run_hash,
        "case_file": case,
        "warnings": compiled.warnings,
    }
