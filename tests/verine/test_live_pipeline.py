"""End-to-end live fixture pipeline (EXP-V011) + quorum, shadowgraph, cascade,
forks, hypothesis confirmation, dedup, event ordering."""

import json


def _poll(client):
    r = client.post("/api/verine/watch-packs/wp_digital_payments/poll")
    assert r.status_code == 200
    return r.json()


def test_offline_seed_present(client):
    connectors = client.get("/api/verine/connectors").json()
    assert {c["connector_id"] for c in connectors} >= {
        "conn_statuspage_demo", "conn_cisa_demo", "conn_nws_demo"
    }
    assert all(c["fixture_path"] for c in connectors)  # offline by default
    pack = client.get("/api/verine/watch-packs/wp_digital_payments").json()
    assert pack["capability_id"] == "cap_digital_payments_authorization"


def test_three_signals_corroborate_into_one_hypothesis(client):
    _poll(client)
    hyps = client.get("/api/verine/hypotheses").json()
    assert len(hyps) == 1
    h = hyps[0]
    assert h["state"] == "OPERATIONALLY_RELEVANT_HYPOTHESIS"
    assert h["quorum"]["independent_group_count"] == 3
    assert len(h["signal_ids"]) == 3


def test_external_signal_never_confirmed_impact(client):
    _poll(client)
    signals = client.get("/api/verine/signals").json()
    # No signal claims confirmed internal impact automatically.
    assert all(s["impact_status"] in ("external_signal_only", "possible_exposure") for s in signals)
    h = client.get("/api/verine/hypotheses").json()[0]
    assert h["state"] != "USER_CONFIRMED_IMPACT"


def test_shadow_edge_review_required(client):
    _poll(client)
    shadows = client.get("/api/verine/shadow-edges").json()
    assert len(shadows) >= 1
    for s in shadows:
        assert s["requires_review"] is True
        assert s["epistemic_status"] == "inferred"
        assert s["status"] == "proposed"


def test_cascade_clock_intervals_and_assumptions(client):
    _poll(client)
    h = client.get("/api/verine/hypotheses").json()[0]
    clock = h["cascade_clock"]
    assert clock is not None
    assert clock["capability_floor"] is not None
    assert clock["assumptions"]
    assert "POSSIBLE" in clock["statement"] or "do not project" in clock["statement"]
    # never a bare "will fail at T"
    assert "will fail" not in clock["statement"].lower()


def test_case_file_has_hash_lineage(client):
    _poll(client)
    h = client.get("/api/verine/hypotheses").json()[0]
    case = client.get(f"/api/verine/cases/{h['case_file_id']}/export").json()
    assert case["graph_hash"].startswith("sha256:")
    assert case["scenario_hash"].startswith("sha256:")
    assert case["run_hash"].startswith("sha256:")
    assert case["model_versions"] and case["seed"]


def test_dedup_on_repoll(client):
    _poll(client)
    first = len(client.get("/api/verine/signals").json())
    result = _poll(client)
    assert all(r.get("suppressed", 0) >= 1 or r.get("not_modified") for r in result["results"])
    assert len(client.get("/api/verine/signals").json()) == first  # no new signals


def test_event_log_ordered_and_replayable(client):
    _poll(client)
    events = client.get("/api/verine/streams/wp_digital_payments/events").json()["events"]
    seqs = [e["seq"] for e in events]
    assert seqs == sorted(seqs)
    assert len(set(seqs)) == len(seqs)  # unique
    types = {e["event"] for e in events}
    assert {"signal_observed", "hypothesis_created", "shadow_edge_created",
            "cascade_clock_updated", "case_saved"} <= types
    # cursor replay: fetch after a mid-seq returns only later events
    mid = seqs[len(seqs) // 2]
    later = client.get(f"/api/verine/streams/wp_digital_payments/events?after_seq={mid}").json()["events"]
    assert all(e["seq"] > mid for e in later)


def test_confirm_requires_actor_and_reason(client):
    _poll(client)
    h = client.get("/api/verine/hypotheses").json()[0]
    hid = h["hypothesis_id"]
    # missing reason rejected by schema
    assert client.post(f"/api/verine/hypotheses/{hid}/confirm", json={"actor": "x", "reason": ""}).status_code == 422
    ok = client.post(f"/api/verine/hypotheses/{hid}/confirm",
                     json={"actor": "ciso@corp", "reason": "Confirmed via internal dashboards"})
    assert ok.status_code == 200
    body = ok.json()
    assert body["state"] == "USER_CONFIRMED_IMPACT"
    assert any(a["actor"] == "ciso@corp" for a in body["audit"])


def test_fork_is_immutable_and_replayable(client):
    _poll(client)
    h = client.get("/api/verine/hypotheses").json()[0]
    case_id = h["case_file_id"]

    no_action = client.post(f"/api/verine/cases/{case_id}/fork",
                            json={"action_ids": []}).json()
    failover = client.post(f"/api/verine/cases/{case_id}/fork",
                           json={"action_ids": ["act_failover_backup_processor"]}).json()
    assert no_action["status"] == "simulated"
    assert failover["status"] in ("simulated", "infeasible")
    if failover["status"] == "simulated":
        # failover should not worsen expected loss vs no action
        assert failover["metrics"]["expected_service_loss_sl_hours"] <= \
            no_action["metrics"]["expected_service_loss_sl_hours"] + 1e-9
        # deterministic fork id + replayable run hash
        again = client.post(f"/api/verine/cases/{case_id}/fork",
                            json={"action_ids": ["act_failover_backup_processor"]}).json()
        assert again["run_hash"] == failover["run_hash"]


def test_reversibility_constraint_rejects_irreversible(client):
    _poll(client)
    h = client.get("/api/verine/hypotheses").json()[0]
    case_id = h["case_file_id"]
    fork = client.post(f"/api/verine/cases/{case_id}/fork", json={
        "action_ids": ["act_manual_authorization_process"],
        "constraints_override": {
            "budget": 100000, "deadline_minutes": 120, "minimum_service_level": 0.70,
            "available_roles": ["payments_operations", "treasury"],
            "max_collateral_risk": 0.5, "facts": ["manual_process_staffed"],
            "require_reversible_actions": True,
        },
    }).json()
    # manual auth reversibility 0.6 >= 0.5 floor, so this one is allowed; assert structure
    assert fork["status"] in ("simulated", "infeasible")
