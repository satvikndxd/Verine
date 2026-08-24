"""Typed repository layer.

v0.1 ships a file-backed JSON store (ADR-001: no Postgres in the sandbox).
The interface mirrors db/migrations/001_initial.sql so a Postgres-backed
implementation can be swapped in without touching routers or domain code.
Graph snapshots are immutable: an id or graph hash cannot be overwritten with
different content.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from ..common.errors import ConflictError, NotFoundError
from ..common.hashing import canonical_json, hash_obj

MAX_DOC_BYTES = 20 * 1024 * 1024


class FileStore:
    """One JSON document per id, per collection. Atomic writes."""

    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, collection: str, doc_id: str) -> Path:
        safe = doc_id.replace("/", "_")
        return self.root / collection / f"{safe}.json"

    def put(self, collection: str, doc_id: str, doc: dict, immutable: bool = False) -> None:
        payload = canonical_json(doc)
        if len(payload) > MAX_DOC_BYTES:
            raise ConflictError(f"Document {doc_id} exceeds size limit")
        path = self._path(collection, doc_id)
        if path.exists():
            existing = path.read_text()
            if immutable and hash_obj(json.loads(existing)) != hash_obj(doc):
                raise ConflictError(
                    f"{collection}/{doc_id} is immutable and already exists with different content"
                )
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as f:
                f.write(payload)
            os.replace(tmp, path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    def get(self, collection: str, doc_id: str) -> dict:
        path = self._path(collection, doc_id)
        if not path.exists():
            raise NotFoundError(f"{collection}/{doc_id} not found")
        return json.loads(path.read_text())

    def exists(self, collection: str, doc_id: str) -> bool:
        return self._path(collection, doc_id).exists()

    def list_ids(self, collection: str) -> list[str]:
        d = self.root / collection
        if not d.exists():
            return []
        return sorted(p.stem for p in d.glob("*.json"))

    def list_all(self, collection: str) -> list[dict]:
        return [self.get(collection, i) for i in self.list_ids(collection)]


class Repositories:
    """Named collections matching the SQL schema."""

    CAPABILITIES = "capabilities"
    SNAPSHOTS = "graph_snapshots"
    INCIDENTS = "incidents"
    SCENARIOS = "scenarios"
    RUNS = "simulation_runs"
    CASES = "case_files"
    EVIDENCE = "evidence"
    ASSUMPTIONS = "assumptions"
    ACTIONS = "actions"

    def __init__(self, store: FileStore):
        self.store = store

    # --- graph snapshots (immutable) -------------------------------------
    def put_snapshot(self, snapshot_doc: dict, graph_hash: str, epistemic_summary: dict) -> None:
        doc = {
            "id": snapshot_doc["graph_snapshot_id"],
            "version": snapshot_doc.get("version", "v1"),
            "graph_json": snapshot_doc,
            "graph_hash": graph_hash,
            "epistemic_summary": epistemic_summary,
        }
        self.store.put(self.SNAPSHOTS, doc["id"], doc, immutable=True)

    def get_snapshot(self, snapshot_id: str) -> dict:
        return self.store.get(self.SNAPSHOTS, snapshot_id)
