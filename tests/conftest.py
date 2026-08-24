import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from sim_helpers import make_scenario  # noqa: E402,F401  (re-exported for tests)

from verine.fixtures import load_fixture  # noqa: E402
from verine.simulation.compiler import compile_scenario  # noqa: E402


@pytest.fixture(scope="session")
def bundle():
    return load_fixture(ROOT / "fixtures" / "digital_payments_capability.json")


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
