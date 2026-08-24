"""Shared simulation-test helpers (imported by unit/simulation/replay tests).

Lives in a uniquely-named module so it never collides with either package's
conftest.py under pytest's default import mode."""

from __future__ import annotations

from verine.simulation.scenarios import Scenario


def make_scenario(bundle, incident_id="inc_compound_payment_crisis", **kw):
    defaults = dict(
        scenario_id="scn_test_001",
        capability_id=bundle.capability.capability_id,
        graph_snapshot_id=bundle.snapshot.graph_snapshot_id,
        incident_id=incident_id,
        constraints=bundle.default_constraints,
        seed=bundle.default_seed,
        horizon_minutes=720,
        monte_carlo_replications=25,
        model_set=["deterministic_propagation_v1"],
        created_at="2026-08-24T09:00:00Z",
    )
    defaults.update(kw)
    return Scenario(**defaults)
