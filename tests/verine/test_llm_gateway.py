"""LLM gateway: model catalog, cited structured output, citation enforcement,
budget limits, and system-still-works-without-LLM (EXP-V009/V010)."""

from verine.providers.llm.validation import validate_structured_output


def _cred(client, provider="openrouter", key="valid-key"):
    return client.post("/api/verine/credentials",
                       json={"provider_id": provider, "api_key": key}).json()["credential_id"]


def test_model_catalog_via_backend(client):
    cid = _cred(client)
    r = client.get(f"/api/verine/providers/openrouter/models?credential_id={cid}")
    assert r.status_code == 200
    models = r.json()["models"]
    assert models and models[0]["model_id"] == "demo/model-a"
    assert models[0]["prompt_cost_per_mtok"] is not None  # cost metadata surfaced


def test_credential_test_reports_health(client):
    cid = _cred(client)
    r = client.post(f"/api/verine/credentials/{cid}/test").json()
    assert r["health"]["status"] == "success"
    assert r["credential"]["last_test_status"] == "success"


def test_bad_key_reports_auth_error(client):
    cid = _cred(client, key="wrong-key")
    r = client.post(f"/api/verine/credentials/{cid}/test").json()
    assert r["health"]["status"] == "auth_error"


def test_cited_incident_summary(client):
    client.post("/api/verine/watch-packs/wp_digital_payments/poll")
    h = client.get("/api/verine/hypotheses").json()[0]
    cid = _cred(client)
    r = client.post("/api/verine/llm/complete", json={
        "credential_id": cid, "model": "demo/model-a", "task": "incident_summarize",
        "hypothesis_id": h["hypothesis_id"], "watch_pack_id": "wp_digital_payments",
    })
    assert r.status_code == 200
    run = r.json()
    assert run["validation"]["valid"] is True
    assert run["structured"]["confidence_status"] == "limited"
    assert run["prompt_hash"].startswith("sha256:")
    assert run["response_hash"].startswith("sha256:")


def test_citation_enforcement_flags_unknown_evidence():
    content = (
        '{"title":"t","what_was_observed":[{"claim":"x","evidence_ids":["ev_fake"]}],'
        '"what_is_inferred":[],"what_is_simulated":[],"unknowns":[],'
        '"evidence_ids":["ev_fake"],"confidence_status":"limited"}'
    )
    result = validate_structured_output(content, "IncidentSummary", known_evidence_ids={"ev_real"})
    assert result["valid"] is False
    assert any("not in case" in e for e in result["errors"])


def test_uncited_claim_marked_unsupported():
    content = (
        '{"title":"t","what_was_observed":["a bare uncited claim"],'
        '"what_is_inferred":[],"what_is_simulated":[],"unknowns":[],'
        '"evidence_ids":[],"confidence_status":"limited"}'
    )
    result = validate_structured_output(content, "IncidentSummary", known_evidence_ids=set())
    assert "a bare uncited claim" in result["unsupported_claims"]


def test_budget_limit_blocks_requests(client, monkeypatch):
    monkeypatch.setenv("VERINE_LLM_REQUESTS_PER_HOUR", "2")
    client.post("/api/verine/watch-packs/wp_digital_payments/poll")
    h = client.get("/api/verine/hypotheses").json()[0]["hypothesis_id"]
    cid = _cred(client)
    payload = {"credential_id": cid, "model": "demo/model-a", "task": "incident_summarize",
               "hypothesis_id": h}
    assert client.post("/api/verine/llm/complete", json=payload).status_code == 200
    assert client.post("/api/verine/llm/complete", json=payload).status_code == 200
    blocked = client.post("/api/verine/llm/complete", json=payload)
    assert blocked.status_code == 422
    assert blocked.json()["error_code"] == "LLM_BUDGET_EXCEEDED"


def test_system_works_without_llm(client):
    """The full pipeline (signals → hypothesis → cascade → case → fork) requires
    no LLM credential at all."""
    client.post("/api/verine/watch-packs/wp_digital_payments/poll")
    h = client.get("/api/verine/hypotheses").json()[0]
    assert h["cascade_clock"] is not None
    assert h["case_file_id"]
    assert client.get("/api/verine/credentials").json() == []  # no LLM configured
