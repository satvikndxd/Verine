"""Encrypted credential store on top of the existing FileStore.

- Plaintext is encrypted before it touches disk and never serialized elsewhere.
- File permissions are tightened to user-only where the OS supports it.
- Decryption registers the plaintext with the redactor so it can never leak
  through logs or error payloads.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from ..common.errors import NotFoundError, VerineError
from ..common.ids import derived_id
from ..common.redaction import register_secret
from ..api.repositories import FileStore
from .contracts import SUPPORTED_LLM_PROVIDERS, Credential, CredentialCreate, CredentialMeta
from .encryption import decrypt, encrypt

COLLECTION = "credentials"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class VaultStore:
    def __init__(self, store: FileStore):
        self.store = store
        self._harden(store.root / COLLECTION)

    @staticmethod
    def _harden(path: Path) -> None:
        try:
            path.mkdir(parents=True, exist_ok=True)
            os.chmod(path, 0o700)
        except OSError:
            pass  # best effort on non-POSIX filesystems

    def create(self, body: CredentialCreate) -> CredentialMeta:
        if body.provider_id not in SUPPORTED_LLM_PROVIDERS:
            raise VerineError(f"Unsupported provider {body.provider_id!r}")
        if body.provider_id != "ollama_local" and not body.api_key:
            raise VerineError("api_key is required for this provider")
        enc = encrypt(body.api_key or "")
        cred = Credential(
            credential_id=derived_id("credential", {"p": body.provider_id, "t": _now(), "n": os.urandom(8).hex()}),
            provider_id=body.provider_id,
            label=body.label,
            key_last4=body.api_key[-4:] if body.api_key else "",
            created_at=_now(),
            updated_at=_now(),
            usage_budget_cents=body.usage_budget_cents,
            base_url=body.base_url,
            default_model=body.default_model,
            **enc,
        )
        self.store.put(COLLECTION, cred.credential_id, cred.model_dump(mode="json"))
        self._harden_file(cred.credential_id)
        return cred.to_meta()

    def _harden_file(self, cred_id: str) -> None:
        try:
            os.chmod(self.store._path(COLLECTION, cred_id), 0o600)
        except OSError:
            pass

    def get(self, cred_id: str) -> Credential:
        return Credential(**self.store.get(COLLECTION, cred_id))

    def list_meta(self) -> list[CredentialMeta]:
        return [Credential(**d).to_meta() for d in self.store.list_all(COLLECTION)]

    def decrypt_key(self, cred_id: str) -> str:
        """Return plaintext for in-request use only. Registers with redactor."""
        cred = self.get(cred_id)
        plaintext = decrypt(cred.ciphertext, cred.salt, cred.nonce)
        register_secret(plaintext)
        return plaintext

    def update(self, cred_id: str, patch: dict) -> CredentialMeta:
        cred = self.get(cred_id)
        allowed = {"label", "enabled", "usage_budget_cents", "default_model", "base_url"}
        data = cred.model_dump(mode="json")
        for k, v in patch.items():
            if k in allowed:
                data[k] = v
        if patch.get("api_key"):
            data.update(encrypt(patch["api_key"]))
            data["key_last4"] = patch["api_key"][-4:]
        data["updated_at"] = _now()
        updated = Credential(**data)
        self.store.put(COLLECTION, cred_id, updated.model_dump(mode="json"))
        self._harden_file(cred_id)
        return updated.to_meta()

    def record_test(self, cred_id: str, status: str) -> CredentialMeta:
        cred = self.get(cred_id)
        data = cred.model_dump(mode="json")
        data["last_tested_at"] = _now()
        data["last_test_status"] = status
        updated = Credential(**data)
        self.store.put(COLLECTION, cred_id, updated.model_dump(mode="json"))
        return updated.to_meta()

    def delete(self, cred_id: str) -> None:
        path = self.store._path(COLLECTION, cred_id)
        if not path.exists():
            raise NotFoundError(f"credentials/{cred_id} not found")
        path.unlink()
