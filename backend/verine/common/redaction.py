"""Secret redaction. Applied to logs, error payloads, and exports.

Fail-safe posture: anything that looks like an API key or bearer token is
scrubbed before it can leave the process. Vault plaintext is additionally
registered at decrypt time and scrubbed verbatim.
"""

from __future__ import annotations

import re
from typing import Any

_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_\-]{8,}"),              # OpenAI/OpenRouter-style
    re.compile(r"sk-ant-[A-Za-z0-9_\-]{8,}"),          # Anthropic
    re.compile(r"(?i)bearer\s+[A-Za-z0-9_\-.]{12,}"),  # Authorization headers
    re.compile(r"(?i)(api[_-]?key|authorization|x-api-key)[\"'\s:=]+[A-Za-z0-9_\-.]{8,}"),
]

REDACTED = "[REDACTED]"

# Plaintext secrets registered while in memory; scrubbed verbatim.
_runtime_secrets: set[str] = set()


def register_secret(value: str) -> None:
    if value and len(value) >= 6:
        _runtime_secrets.add(value)


def clear_secrets() -> None:
    _runtime_secrets.clear()


def redact_text(text: str) -> str:
    for secret in _runtime_secrets:
        if secret in text:
            text = text.replace(secret, REDACTED)
    for pat in _PATTERNS:
        text = pat.sub(REDACTED, text)
    return text


def redact_obj(obj: Any) -> Any:
    if isinstance(obj, str):
        return redact_text(obj)
    if isinstance(obj, dict):
        return {k: REDACTED if _is_secret_key(k) else redact_obj(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [redact_obj(v) for v in obj]
    return obj


def _is_secret_key(key: str) -> bool:
    k = key.lower()
    return any(s in k for s in ("api_key", "apikey", "secret", "password", "token", "plaintext"))
