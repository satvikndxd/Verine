"""Benchmark runner for tasks B1-B10 (section 13.1 of the build brief).

Engineering benchmarks (B1-B7, B9) execute against the fixture. Human
benchmarks (B8, B10) are recorded as `pending` until a real exercise runs —
results are never manufactured.
"""

from __future__ import annotations

from ..cases.runner import execute_scenario
from ..optimization.constraints import check_action_set


def run_benchmarks(svc) -> dict:
    tasks: list[dict] = []
    meta = svc.fixture_meta()

    scenario, compiled = svc.compile_and_store_scenario(
        capability_id="cap_digital_payments_authorization",
        incident_id="inc_compound_payment_crisis",
    )
    result = svc.run_simulation(scenario.scenario_id)

    # B1 determinism
    result2 = execute_scenario(compiled, svc.list_actions())
    tasks.append(
        {
            "task_id": "B1",
            "name": "Graph validates and replays deterministically",
            "baseline": "hash and schema checks",
            "status": "pass" if result2["run_hash"] == result["run_hash"] else "fail",
            "detail": {"run_hash": result["run_hash"], "graph_warnings": meta["graph_warnings"]},
        }
    )

    # B2 affected nodes vs direct reachability
    det_nodes = set(
        result["model_outputs"]["deterministic_propagation_v1"]["metrics"]["affected_nodes"]
    )
    reach_nodes = set(result["model_outputs"]["reachability_v1"]["affected_nodes"])
    tasks.append(
        {
            "task_id": "B2",
            "name": "Simulator identifies affected nodes",
            "baseline": "direct reachability (upper bound)",
            "status": "pass" if det_nodes and det_nodes <= reach_nodes else "fail",
            "detail": {
                "deterministic_affected": len(det_nodes),
                "reachability_upper_bound": len(reach_nodes),
                "subset_of_upper_bound": det_nodes <= reach_nodes,
            },
        }
    )

    # B3 capacity-flow bottleneck
    cf = result["model_outputs"]["capacity_flow_v1"]["capabilities"]["cap_digital_payments_authorization"]
    tasks.append(
        {
            "task_id": "B3",
            "name": "Capacity-flow identifies bottleneck chain",
            "baseline": "degree/centrality",
            "status": "pass" if cf["bottleneck_edges"] else "fail",
            "detail": {"bottleneck_nodes": cf["bottleneck_nodes"], "bottleneck_edges": cf["bottleneck_edges"]},
        }
    )

    # B4 Monte Carlo uncertainty
    mc = result["model_outputs"]["monte_carlo_v1"]["aggregates"]["max_degradation"]
    spread = mc["p90"] is not None and mc["p10"] is not None and mc["p90"] > mc["p10"]
    tasks.append(
        {
            "task_id": "B4",
            "name": "Monte Carlo quantifies uncertainty (quantile spread, not a point)",
            "baseline": "point estimate",
            "status": "pass" if spread else "fail",
            "detail": mc,
        }
    )

    # B5 containment feasibility
    cont = result["containment"]
    all_ranked_feasible = True
    amap = {a.action_id: a for a in svc.list_actions()}
    for s in ([cont["chosen_set"]] if cont["chosen_set"] else []) + cont["runner_up_sets"]:
        ok, _ = check_action_set([amap[i] for i in s["action_ids"]], compiled.scenario.constraints)
        all_ranked_feasible &= ok
    tasks.append(
        {
            "task_id": "B5",
            "name": "Optimizer ranks only feasible containment sets",
            "baseline": "greedy action ranking",
            "status": "pass" if all_ranked_feasible and cont["rejected_count"] > 0 else "fail",
            "detail": {
                "chosen": cont["chosen_set"]["action_ids"] if cont["chosen_set"] else None,
                "rejected_count": cont["rejected_count"],
            },
        }
    )

    # B6 hidden dependency raises uncertainty
    scn_hidden, compiled_hidden = svc.compile_and_store_scenario(
        capability_id="cap_digital_payments_authorization",
        incident_id="inc_compound_payment_crisis",
        hidden_edge_ids=["edge_idp_region", "edge_backup_region"],
    )
    hidden_result = svc.run_simulation(scn_hidden.scenario_id)
    u_full = result["unknowns"]["uncertainty"]["epistemic"]
    u_hidden = hidden_result["unknowns"]["uncertainty"]["epistemic"]
    tasks.append(
        {
            "task_id": "B6",
            "name": "Hidden-dependency scenario increases uncertainty",
            "baseline": "complete graph",
            "status": "pass" if u_hidden > u_full else "fail",
            "detail": {"epistemic_full": u_full, "epistemic_hidden": u_hidden},
        }
    )

    # B7 disagreement localization
    areas = result["disagreement"]["areas"]
    explained = bool(areas) and all(a["likely_reasons"] and a["recommended_next_step"] for a in areas)
    tasks.append(
        {
            "task_id": "B7",
            "name": "Model disagreement locates assumption conflicts with reasons",
            "baseline": "ensemble average",
            "status": "pass" if explained else "fail",
            "detail": {"overall_level": result["disagreement"]["overall_level"], "areas": len(areas)},
        }
    )

    # B8 human speed comparison — requires a human exercise
    tasks.append(
        {
            "task_id": "B8",
            "name": "Human finds critical dependency faster with the tool",
            "baseline": "manual graph inspection",
            "status": "pending",
            "detail": {"reason": "Requires human tabletop exercise (EXP-N006); results are never manufactured."},
        }
    )

    # B9 case replay byte-for-byte
    verdict = svc.replay(result["case_file"]["case_file_id"])
    tasks.append(
        {
            "task_id": "B9",
            "name": "Case file replays byte-for-byte",
            "baseline": "re-run comparison",
            "status": "pass" if verdict.get("hashes_match") else "fail",
            "detail": verdict,
        }
    )

    # B10 decision quality — requires human study
    tasks.append(
        {
            "task_id": "B10",
            "name": "Output improves decision quality",
            "baseline": "human-only tabletop exercise",
            "status": "pending",
            "detail": {"reason": "Requires human tabletop exercise (EXP-N006); results are never manufactured."},
        }
    )

    return {
        "benchmark": "verine_nerve_v0_1",
        "fixture_id": meta["fixture_id"],
        "seed": meta["default_seed"],
        "tasks": tasks,
        "note": "Engineering benchmarks over the synthetic fixture. B8/B10 stay pending until humans run them.",
    }
