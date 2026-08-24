from sim_helpers import make_scenario

from verine.cases.replay import replay_case
from verine.cases.runner import execute_scenario
from verine.simulation.compiler import compile_scenario


def test_case_file_replays_byte_for_byte(bundle, compiled_compound):
    result = execute_scenario(compiled_compound, bundle.actions, executed_at="2026-08-24T09:00:00Z")
    case = result["case_file"]
    verdict = replay_case(case, compiled_compound, bundle.actions)
    assert verdict["replayed"] is True
    assert verdict["hashes_match"] is True
    assert verdict["actual_run_hash"] == case.run_hash
    assert verdict["metrics_match"] is True


def test_replay_detects_tampered_scenario(bundle, compiled_compound):
    result = execute_scenario(compiled_compound, bundle.actions, executed_at="2026-08-24T09:00:00Z")
    case = result["case_file"]

    inc = bundle.incidents["inc_compound_payment_crisis"]
    tampered_scn = make_scenario(bundle, seed=99, model_set=compiled_compound.scenario.model_set)
    tampered = compile_scenario(tampered_scn, bundle.snapshot, inc, bundle.actions)
    verdict = replay_case(case, tampered, bundle.actions)
    assert verdict["replayed"] is False
    assert "Scenario hash mismatch" in verdict["reason"]


def test_seed_changes_monte_carlo_hash(bundle):
    inc = bundle.incidents["inc_compound_payment_crisis"]
    models = ["deterministic_propagation_v1", "monte_carlo_v1"]
    r = []
    for seed in (1, 2):
        scn = make_scenario(bundle, seed=seed, model_set=models, monte_carlo_replications=10)
        compiled = compile_scenario(scn, bundle.snapshot, inc, bundle.actions)
        r.append(execute_scenario(compiled, bundle.actions)["run_hash"])
    assert r[0] != r[1]
