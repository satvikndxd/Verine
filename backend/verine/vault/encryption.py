"""Authenticated encryption for the credential vault (AES-256-GCM).

Key derivation: scrypt(VERINE_VAULT_KEY passphrase, per-credential salt).
Fail-closed: without a vault key, encryption and decryption raise VaultLocked.
"""

from __future__ import annotations

import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

from ..common.errors import VerineError


class VaultLocked(VerineError):
    error_code = "VAULT_LOCKED"


def _passphrase() -> bytes:
    key = os.environ.get("VERINE_VAULT_KEY", "")
    if not key:
        raise VaultLocked(
            "Vault key not configured. Set VERINE_VAULT_KEY to enable credential storage."
        )
    return key.encode("utf-8")


def _derive(passphrase: bytes, salt: bytes) -> bytes:
    return Scrypt(salt=salt, length=32, n=2**14, r=8, p=1).derive(passphrase)


def encrypt(plaintext: str) -> dict:
    """Return {ciphertext, salt, nonce} as base64 strings."""
    passphrase = _passphrase()
    salt = os.urandom(16)
    nonce = os.urandom(12)
    key = _derive(passphrase, salt)
    ct = AESGCM(key).encrypt(nonce, plaintext.encode("utf-8"), b"verine_vault_v1")
    return {
        "ciphertext": base64.b64encode(ct).decode(),
        "salt": base64.b64encode(salt).decode(),
        "nonce": base64.b64encode(nonce).decode(),
    }


def decrypt(ciphertext_b64: str, salt_b64: str, nonce_b64: str) -> str:
    passphrase = _passphrase()
    key = _derive(passphrase, base64.b64decode(salt_b64))
    pt = AESGCM(key).decrypt(
        base64.b64decode(nonce_b64), base64.b64decode(ciphertext_b64), b"verine_vault_v1"
    )
    return pt.decode("utf-8")
