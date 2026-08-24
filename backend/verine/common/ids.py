"""Canonical ID utilities.

IDs are prefixed, lowercase, and stable. Deterministic IDs can be derived from
content hashes so replays produce identical identifiers.
"""

from __future__ import annotations

import re
from typing import Any

from .hashing import hash_obj

_ID_RE = re.compile(r"^[a-z][a-z0-9_]*_[a-z0-9][a-z0-9_\-]*$")

PREFIXES = {
    "capability": "cap",
    "node": "node",
    "edge": "edge",
    "incident": "inc",
    "scenario": "scn",
    "run": "run",
    "case": "case",
    "evidence": "ev",
    "assumption": "asm",
    "action": "act",
    "graph": "graph",
    "experiment": "exp",
    "credential": "cred",
    "connector": "conn",
    "signal": "sig",
    "watch_pack": "wp",
    "hypothesis": "hyp",
    "shadow_edge": "shadow",
    "fork": "fork",
    "event": "evt",
    "llm_request": "llmreq",
}


def is_valid_id(value: str) -> bool:
    return bool(_ID_RE.match(value)) and len(value) <= 128


def validate_id(value: str, kind: str | None = None) -> str:
    if not is_valid_id(value):
        raise ValueError(f"Invalid id: {value!r}")
    if kind is not None:
        prefix = PREFIXES.get(kind, kind)
        if not value.startswith(prefix + "_"):
            raise ValueError(f"Id {value!r} must start with prefix {prefix!r}_")
    return value


def derived_id(kind: str, payload: Any) -> str:
    """Deterministic content-derived id (12 hex chars of canonical hash)."""
    prefix = PREFIXES.get(kind, kind)
    digest = hash_obj(payload).removeprefix("sha256:")[:12]
    return f"{prefix}_{digest}"
