"""Cascade clock: interval-based time projections with explicit assumptions.

All intervals come from declared model outputs (deterministic pathway lags and
Monte Carlo quantiles). Language contract: "the model projects a possible
capability-floor breach between X and Y minutes under current assumptions" —
never "will fail at T"."""

from __future__ import annotations


def _mc_interval(agg: dict | None) -> dict | None:
    if not agg or agg.get("median") is None:
        return None
    return {"low": agg.get("p10"), "median": agg.get("median"), "high": agg.get("p90")}


def build_cascade_clock(run_result: dict, capability_id: str, snapshot_edges: list[dict]) -> dict:
    det = run_result["model_outputs"].get("deterministic_propagation_v1")
    mc = run_result["model_outputs"].get("monte_carlo_v1")
    edge_by_id = {e["edge_id"]: e for e in snapshot_edges}

    # Next-node interval from the driving pathway's first-hop lag interval.
    next_node = None
    if det and det.get("pathways"):
        top = det["pathways"][0]
        lags_min = lags_med = lags_max = 0.0
        for eid in top["edge_chain"][:1]:
            lag = edge_by_id.get(eid, {}).get("propagation_lag_minutes", {})
            lags_min += lag.get("min", 0)
            lags_med += lag.get("median", 0)
            lags_max += lag.get("max", 0)
        next_node = {
            "low": round(lags_min), "median": round(lags_med), "high": round(lags_max),
            "node_id": top["node_chain"][1] if len(top["node_chain"]) > 1 else None,
            "via_pathway": top["description"],
        }

    floor = None
    breach_fraction = None
    if mc:
        floor = _mc_interval(mc["aggregates"].get("time_to_floor_minutes"))
        breach_fraction = mc.get("floor_breach_fraction")
    if floor is None and det:
        ttf = det["metrics"]["capabilities"][capability_id].get("time_to_floor_minutes")
        if ttf is not None:
            floor = {"low": ttf, "median": ttf, "high": ttf}

    recovery = _mc_interval(mc["aggregates"].get("recovery_time_minutes")) if mc else None
    if recovery is None and det:
        rec = det["metrics"]["capabilities"][capability_id].get("recovery_time_minutes")
        if rec is not None:
            recovery = {"low": rec, "median": rec, "high": rec}

    assumptions = [a["statement"] for a in (det.get("assumptions", []) if det else [])]
    assumptions.append("Incident severity/duration are declared inferred inputs, not measurements.")

    statement = None
    if floor and floor.get("median") is not None:
        low = floor.get("low") if floor.get("low") is not None else floor["median"]
        high = floor.get("high") if floor.get("high") is not None else floor["median"]
        statement = (
            f"The model projects a POSSIBLE capability-floor breach between "
            f"{round(low)} and {round(high)} minutes under the current graph and assumptions"
            + (f" (breached in {round(breach_fraction * 100)}% of replications)." if breach_fraction is not None else ".")
        )
    else:
        statement = "The models do not project a capability-floor breach under current assumptions."

    return {
        "current": {"low": 0, "median": 0, "high": 0},
        "next_node": next_node,
        "capability_floor": floor,
        "floor_breach_fraction": breach_fraction,
        "recovery": recovery,
        "unit": "minutes",
        "statement": statement,
        "assumptions": assumptions,
        "epistemic_status": "model_result",
    }
