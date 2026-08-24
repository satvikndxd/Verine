"""Canonical JSON serialization and SHA-256 hashing.

Determinism contract: two semantically equal payloads (same keys/values, any
key order) must produce identical bytes and therefore identical hashes.
Floats are rejected unless they are finite; NaN/Infinity would break canonical
round-tripping.
"""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any


def _reject_non_finite(obj: Any) -> Any:
    if isinstance(obj, float) and not math.isfinite(obj):
        raise ValueError("Non-finite float is not allowed in canonical JSON")
    if isinstance(obj, dict):
        for k, v in obj.items():
            if not isinstance(k, str):
                raise ValueError(f"Non-string key {k!r} is not allowed in canonical JSON")
            _reject_non_finite(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            _reject_non_finite(v)
    return obj


def canonical_json(obj: Any) -> str:
    """Serialize to canonical JSON: sorted keys, compact separators, UTF-8."""
    _reject_non_finite(obj)
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def sha256_hex(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return "sha256:" + hashlib.sha256(data).hexdigest()


def hash_obj(obj: Any) -> str:
    """Canonical hash of a JSON-serializable object."""
    return sha256_hex(canonical_json(obj))
