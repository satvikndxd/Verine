"""Align model outputs on a common comparison schema."""

from __future__ import annotations

from ..simulation.state import PropagationResult


def extract_comparable(model_output: PropagationResult | dict, capability_id: str) -> dict:
    """Normalize each model's output into {max_degradation, time_to_floor, recovery, affected}."""
    if isinstance(model_output, PropagationResult):
        cm = model_output.metrics["capabilities"][capability_id]
        return {
            "model_id": model_output.model_id,
            "max_degradation": cm["max_degradation"],
            "min_service_level": cm["min_service_level"],
            "time_to_floor_minutes": cm["time_to_floor_minutes"],
            "recovery_time_minutes": cm["recovery_time_minutes"],
            "affected_nodes": model_output.metrics["affected_nodes"],
        }
    model_id = model_output.get("model_id", "unknown")
    if model_id == "capacity_flow_v1":
        cm = model_output["capabilities"][capability_id]
        return {
            "model_id": model_id,
            "max_degradation": cm["max_degradation"],
            "min_service_level": cm["min_service_level"],
            "time_to_floor_minutes": cm["time_to_floor_minutes"],
            "recovery_time_minutes": cm["recovery_time_minutes"],
            "affected_nodes": model_output["affected_nodes"],
        }
    if model_id == "monte_carlo_v1":
        agg = model_output["aggregates"]
        return {
            "model_id": model_id,
            "max_degradation": agg["max_degradation"]["median"],
            "min_service_level": agg["min_service_level"]["median"],
            "time_to_floor_minutes": agg["time_to_floor_minutes"]["median"],
            "recovery_time_minutes": agg["recovery_time_minutes"]["median"],
            "affected_nodes": sorted(
                n for n, f in model_output["node_affect_frequency"].items() if f >= 0.5
            ),
        }
    if model_id == "reachability_v1":
        return {
            "model_id": model_id,
            "max_degradation": None,
            "min_service_level": None,
            "time_to_floor_minutes": None,
            "recovery_time_minutes": None,
            "affected_nodes": model_output["affected_nodes"],
        }
    raise ValueError(f"Unknown model output shape for {model_id}")
