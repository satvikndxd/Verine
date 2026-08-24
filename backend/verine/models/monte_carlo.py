"""Monte Carlo model: seeded replications sampling ONLY from declared intervals.

Sampled quantities (each only when an interval is declared in the fixture):
- incident component severity   (component.severity_interval)
- incident component duration   (component.duration_interval_minutes)
- edge propagation lag          (edge.propagation_lag_minutes min/median/max)
- node recovery time            (node.recovery_time_interval_minutes)

Every seed-level result is recorded. Aggregates are quantiles, never a bare mean.
"""

from __future__ import annotations

from ..common.randomness import SeededRng
from ..simulation.compiler import CompiledScenario
from ..simulation.propagate import ParamOverrides, run_propagation

MODEL_ID = "monte_carlo_v1"


def _quantile(sorted_vals: list[float], q: float) -> float:
    if not sorted_vals:
        return 0.0
    idx = q * (len(sorted_vals) - 1)
    lo = int(idx)
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = idx - lo
    return sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac


def run_monte_carlo(compiled: CompiledScenario, replications: int | None = None) -> dict:
    scn = compiled.scenario
    n = replications or scn.monte_carlo_replications
    root = SeededRng(scn.seed, "monte_carlo_v1")

    seed_level: list[dict] = []
    cap_id = scn.capability_id

    for rep in range(n):
        rng = root.substream(f"rep_{rep}")
        ov = ParamOverrides()
        for idx, comp in enumerate(compiled.incident.components):
            if comp.severity_interval is not None:
                iv = comp.severity_interval
                ov.component_severity[idx] = round(rng.triangular(iv.low, iv.median, iv.high), 6)
            if comp.duration_interval_minutes is not None:
                iv = comp.duration_interval_minutes
                ov.component_duration[idx] = int(round(rng.triangular(iv.low, iv.median, iv.high)))
        for e in sorted(compiled.snapshot.edges, key=lambda e: e.edge_id):
            lag = e.propagation_lag_minutes
            if lag.max > lag.min:
                ov.edge_lag_minutes[e.edge_id] = round(rng.triangular(lag.min, lag.median, lag.max), 6)
        for node in sorted(compiled.snapshot.nodes, key=lambda n: n.node_id):
            if node.recovery_time_interval_minutes is not None:
                iv = node.recovery_time_interval_minutes
                ov.node_recovery_minutes[node.node_id] = round(rng.triangular(iv.low, iv.median, iv.high), 6)

        result = run_propagation(
            compiled.snapshot,
            compiled.incident,
            horizon_minutes=scn.horizon_minutes,
            step_minutes=scn.step_minutes,
            hidden_edge_ids=scn.hidden_edge_ids,
            scheduled_actions=scn.scheduled_actions,
            actions_by_id=compiled.actions_by_id,
            overrides=ov,
            model_id=MODEL_ID,
            seed=scn.seed,
            record_steps=False,
        )
        cm = result.metrics["capabilities"][cap_id]
        seed_level.append(
            {
                "replication": rep,
                "max_degradation": cm["max_degradation"],
                "min_service_level": cm["min_service_level"],
                "time_to_floor_minutes": cm["time_to_floor_minutes"],
                "recovery_time_minutes": cm["recovery_time_minutes"],
                "expected_service_loss_sl_hours": cm["expected_service_loss_sl_hours"],
                "affected_node_count": result.metrics["affected_node_count"],
                "affected_nodes": result.metrics["affected_nodes"],
            }
        )

    def agg(key: str, none_as: float | None = None) -> dict:
        vals = []
        n_none = 0
        for s in seed_level:
            v = s[key]
            if v is None:
                n_none += 1
                if none_as is None:
                    continue
                v = none_as
            vals.append(float(v))
        vals.sort()
        return {
            "p10": round(_quantile(vals, 0.10), 6) if vals else None,
            "median": round(_quantile(vals, 0.50), 6) if vals else None,
            "p90": round(_quantile(vals, 0.90), 6) if vals else None,
            "n_null": n_none,
        }

    node_hits: dict[str, int] = {}
    for s in seed_level:
        for nid in s["affected_nodes"]:
            node_hits[nid] = node_hits.get(nid, 0) + 1

    return {
        "model_id": MODEL_ID,
        "epistemic_status": "model_result",
        "replications": n,
        "seed": scn.seed,
        "capability_id": cap_id,
        "aggregates": {
            "max_degradation": agg("max_degradation"),
            "min_service_level": agg("min_service_level"),
            "time_to_floor_minutes": agg("time_to_floor_minutes"),
            "recovery_time_minutes": agg("recovery_time_minutes"),
            "expected_service_loss_sl_hours": agg("expected_service_loss_sl_hours"),
            "affected_node_count": agg("affected_node_count"),
        },
        "floor_breach_fraction": round(
            sum(1 for s in seed_level if s["time_to_floor_minutes"] is not None) / n, 6
        ),
        "node_affect_frequency": {k: round(v / n, 6) for k, v in sorted(node_hits.items())},
        "seed_level_results": seed_level,
        "note": "Sampled only from declared fixture intervals; quantiles reported, never a bare mean.",
    }
