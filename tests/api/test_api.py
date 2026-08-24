import pytest
from fastapi.testclient import TestClient

from verine.api.app import create_app

CAP = "cap_digital_payments_authorization"


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    app = create_app(data_dir=tmp_path_factory.mktemp("data"))
    with TestClient(app) as c:
        yield c


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["version"]
    assert "disclaimer" in body


def test_capabilities_seeded(client):
    r = client.get("/api/capabilities")
    assert r.status_code == 200
    assert any(c["capability_id"] == CAP for c in r.json())
    r = client.get(f"/api/capabilities/{CAP}")
    assert r.status_code == 200
    assert len(r.json()["dependencies"]) >= 5


def test_capability_not_found_structured_error(client):
    r = client.get("/api/capabilities/cap_ghost")
    assert r.status_code == 404
    body = r.json()
    assert body["error_code"] == "NOT_FOUND"
    assert body["request_id"].startswith("req_")


def test_snapshot_immutability(client):
    snap = client.get("/api/graph/snapshots/graph_demo_v1")
    assert snap.status_code == 200
    graph = snap.json()["graph_json"]
    mutated = dict(graph)
    mutated["edges"] = graph["edges"][:-1]  # different content, same id
    r = client.post("/api/graph/snapshots", json=mutated)
    assert r.status_code == 409
    assert r.json()["error_code"] == "CONFLICT"


def test_invalid_incident_rejected(client):
    r = client.post(
        "/api/incidents",
        json={
            "incident_id": "inc_bad",
            "name": "Bad",
            "incident_type": "single",
            "onset_at": "2026-08-24T09:00:00Z",
            "duration_minutes": 60,
            "severity": 0.5,
            "components": [
                {"target_node_id": "node_ghost", "mode": "latency", "severity": 0.5, "duration_minutes": 30}
            ],
        },
    )
    assert r.status_code == 422
    assert r.json()["error_code"] == "SCENARIO_INVALID"


def test_scenario_invalid_min_service_level(client):
    r = client.post(
        "/api/scenarios/compile",
        json={
            "capability_id": CAP,
            "incident_id": "inc_compound_payment_crisis",
            "constraints": {
                "budget": 100000,
                "deadline_minutes": 120,
                "minimum_service_level": 0.999,
            },
        },
    )
    assert r.status_code == 422
    body = r.json()
    assert body["error_code"] == "SCENARIO_INVALID"
    assert any("minimum_service_level" in fe["field"] for fe in body["field_errors"])


def _compile(client, **overrides):
    payload = {
        "capability_id": CAP,
        "incident_id": "inc_compound_payment_crisis",
        "monte_carlo_replications": 20,
    }
    payload.update(overrides)
    r = client.post("/api/scenarios/compile", json=payload)
    assert r.status_code == 201, r.text
    return r.json()


def test_full_flow_compile_run_replay(client):
    compiled = _compile(client)
    scenario_id = compiled["scenario"]["scenario_id"]
    assert compiled["scenario_hash"].startswith("sha256:")

    # deterministic scenario id: same body -> same id
    again = _compile(client)
    assert again["scenario"]["scenario_id"] == scenario_id

    r = client.post("/api/simulations/run", json={"scenario_id": scenario_id})
    assert r.status_code == 201, r.text
    run = r.json()
    assert run["run_hash"].startswith("sha256:")
    assert set(run["model_outputs"]) == {
        "reachability_v1",
        "deterministic_propagation_v1",
        "capacity_flow_v1",
        "monte_carlo_v1",
    }
    case = run["case_file"]
    assert case["graph_hash"] and case["scenario_hash"] and case["run_hash"]
    assert case["assumptions"], "case file must carry assumptions"
    assert case["disclaimer"]

    rr = client.get(f"/api/simulations/{run['run_id']}")
    assert rr.status_code == 200
    assert rr.json()["run_hash"] == run["run_hash"]

    cases = client.get("/api/cases").json()
    assert any(c["case_file_id"] == case["case_file_id"] for c in cases)

    replay = client.post(f"/api/cases/{case['case_file_id']}/replay")
    assert replay.status_code == 200
    verdict = replay.json()
    assert verdict["replayed"] is True and verdict["hashes_match"] is True


def test_containment_recompute_with_constraints(client):
    compiled = _compile(client)
    scenario_id = compiled["scenario"]["scenario_id"]
    base = client.post("/api/containment/optimize", json={"scenario_id": scenario_id}).json()
    assert base["chosen_set"] is not None

    tight = client.post(
        "/api/containment/optimize",
        json={
            "scenario_id": scenario_id,
            "constraints_override": {
                "budget": 1500,
                "deadline_minutes": 40,
                "minimum_service_level": 0.7,
                "available_roles": ["payments_operations"],
                "max_collateral_risk": 0.05,
                "facts": [],
            },
        },
    ).json()
    assert tight["rejected_count"] > base["rejected_count"]
    if tight["chosen_set"] is not None:
        assert tight["chosen_set"]["total_cost"] <= 1500


def test_evidence_endpoint(client):
    r = client.get("/api/evidence")
    assert r.status_code == 200
    body = r.json()
    assert len(body["evidence"]) > 40
    assert len(body["assumptions"]) >= 4
    inferred = client.get("/api/evidence", params={"epistemic_status": "simulated"}).json()
    assert all(e["epistemic_status"] == "simulated" for e in inferred["evidence"])


def test_openapi_contract(client):
    spec = client.get("/openapi.json").json()
    paths = spec["paths"]
    required = [
        "/api/health",
        "/api/capabilities",
        "/api/capabilities/{cap_id}",
        "/api/graph/snapshots",
        "/api/graph/snapshots/{snapshot_id}",
        "/api/incidents",
        "/api/incidents/{incident_id}",
        "/api/scenarios/compile",
        "/api/simulations/run",
        "/api/simulations/{run_id}",
        "/api/containment/optimize",
        "/api/cases",
        "/api/cases/{case_id}",
        "/api/cases/{case_id}/replay",
        "/api/evidence",
        "/api/experiments",
    ]
    for route in required:
        assert route in paths, f"missing route {route}"
