"""Vault: encryption round-trip, fail-closed, and no-plaintext-leak guarantees."""

import json

import pytest

from verine.common.redaction import redact_obj, redact_text
from verine.vault.encryption import VaultLocked, decrypt, encrypt


def test_encrypt_round_trip():
    enc = encrypt("sk-secret-123456789")
    assert set(enc) == {"ciphertext", "salt", "nonce"}
    assert "sk-secret" not in enc["ciphertext"]
    assert decrypt(enc["ciphertext"], enc["salt"], enc["nonce"]) == "sk-secret-123456789"


def test_encrypt_fail_closed_without_key(monkeypatch):
    monkeypatch.delenv("VERINE_VAULT_KEY", raising=False)
    with pytest.raises(VaultLocked):
        encrypt("secret")


def test_wrong_key_fails(monkeypatch):
    monkeypatch.setenv("VERINE_VAULT_KEY", "key-one")
    enc = encrypt("sk-secret-abcdef")
    monkeypatch.setenv("VERINE_VAULT_KEY", "key-two")
    with pytest.raises(Exception):
        decrypt(enc["ciphertext"], enc["salt"], enc["nonce"])


def test_credential_api_never_returns_plaintext(client):
    r = client.post("/api/verine/credentials", json={
        "provider_id": "openrouter", "api_key": "sk-or-verysecret-7f3a", "label": "Test",
    })
    assert r.status_code == 201
    body = r.json()
    assert "sk-or-verysecret" not in json.dumps(body)
    assert body["masked"].endswith("7f3a")
    assert "ciphertext" not in body and "api_key" not in body

    listed = client.get("/api/verine/credentials").json()
    assert "sk-or-verysecret" not in json.dumps(listed)

    # The stored document holds ciphertext only, never plaintext.
    from verine.api.live_service import get_live_service
    cred = get_live_service().vault.get(body["credential_id"])
    assert "sk-or-verysecret" not in cred.model_dump_json()
    assert cred.key_last4 == "7f3a"


def test_redaction_scrubs_keys():
    assert "sk-abcdefghij" not in redact_text("token sk-abcdefghijklmnop here")
    obj = {"api_key": "sk-secret", "nested": {"authorization": "Bearer sk-xyzabcdef"}}
    red = redact_obj(obj)
    assert red["api_key"] == "[REDACTED]"
    assert "sk-xyzabcdef" not in json.dumps(red)


def test_delete_credential(client):
    cid = client.post("/api/verine/credentials", json={
        "provider_id": "openai", "api_key": "sk-todelete-9999",
    }).json()["credential_id"]
    assert client.delete(f"/api/verine/credentials/{cid}").status_code == 204
    assert client.get("/api/verine/credentials").json() == []
