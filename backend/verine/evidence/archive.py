"""Immutable, hash-addressed raw artifact archive.

A changed response becomes a NEW artifact; historical evidence is never
overwritten. Artifacts are stored as data/verine/raw/<sha256>.bin with a
sidecar metadata document."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from ..common.hashing import sha256_hex

MAX_ARTIFACT_BYTES = int(os.environ.get("VERINE_MAX_RESPONSE_BYTES", str(50_000_000)))


class RawArchive:
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def put(self, content: bytes, source_uri: str, connector_id: str,
            status_code: int = 200, headers: dict | None = None) -> dict:
        if len(content) > MAX_ARTIFACT_BYTES:
            raise ValueError("Artifact exceeds size cap")
        digest = sha256_hex(content)
        name = digest.removeprefix("sha256:")
        blob = self.root / f"{name}.bin"
        meta_path = self.root / f"{name}.meta.json"
        if not blob.exists():
            self._atomic_write(blob, content)
        meta = {
            "raw_artifact_hash": digest,
            "source_uri": source_uri,
            "connector_id": connector_id,
            "status_code": status_code,
            "size_bytes": len(content),
            "retrieved_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "headers": {k: v for k, v in (headers or {}).items()
                        if k.lower() in ("etag", "last-modified", "content-type")},
        }
        if not meta_path.exists():
            self._atomic_write(meta_path, json.dumps(meta, indent=2).encode())
        return meta

    def get(self, artifact_hash: str) -> bytes:
        name = artifact_hash.removeprefix("sha256:")
        return (self.root / f"{name}.bin").read_bytes()

    def exists(self, artifact_hash: str) -> bool:
        name = artifact_hash.removeprefix("sha256:")
        return (self.root / f"{name}.bin").exists()

    @staticmethod
    def _atomic_write(path: Path, content: bytes) -> None:
        fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(content)
            os.replace(tmp, path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
