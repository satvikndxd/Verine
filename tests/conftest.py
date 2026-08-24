import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from verine.fixtures import load_fixture  # noqa: E402
from verine.simulation.compiler import compile_scenario  # noqa: E402
from verine.simulation.scenarios import Scenario  # noqa: E402


@pytest.fixture(scope="session")
def bundle():
    return load_fixture(ROOT / "fixtures" / "digital_payments_capability.json")


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


@pytest.fixture()
def compiled_compound(bundle):
    scn = make_scenario(
        bundle,
        model_set=[
            "reachability_v1",
            "deterministic_propagation_v1",
            "capacity_flow_v1",
            "monte_carlo_v1",
        ],
    )
    return compile_scenario(scn, bundle.snapshot, bundle.incidents["inc_compound_payment_crisis"], bundle.actions)
