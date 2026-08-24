"""Append-only per-watch-pack event log with cursor replay and SSE tailing.

Events are JSONL lines with monotonically increasing sequence numbers. SSE
clients reconnect with Last-Event-ID and replay from their cursor without
duplicates. Client disconnects never stop ingestion."""

from __future__ import annotations

import asyncio
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

HEARTBEAT_SECONDS = int(os.environ.get("VERINE_SSE_HEARTBEAT_SECONDS", "20"))


class EventLog:
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self._locks: dict[str, asyncio.Lock] = {}

    def _path(self, stream_id: str) -> Path:
        return self.root / f"{stream_id.replace('/', '_')}.jsonl"

    def append(self, stream_id: str, event_type: str, data: dict) -> dict:
        path = self._path(stream_id)
        seq = self._last_seq(stream_id) + 1
        record = {
            "seq": seq,
            "id": f"evt_{seq:08d}",
            "event": event_type,
            "at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "data": data,
        }
        line = json.dumps(record, separators=(",", ":"), sort_keys=True)
        with open(path, "a") as f:
            f.write(line + "\n")
            f.flush()
            os.fsync(f.fileno())
        return record

    def _last_seq(self, stream_id: str) -> int:
        path = self._path(stream_id)
        if not path.exists():
            return 0
        last = 0
        with open(path) as f:
            for line in f:
                if line.strip():
                    last = json.loads(line)["seq"]
        return last

    def read_since(self, stream_id: str, after_seq: int = 0, limit: int = 500) -> list[dict]:
        path = self._path(stream_id)
        if not path.exists():
            return []
        out = []
        with open(path) as f:
            for line in f:
                if not line.strip():
                    continue
                rec = json.loads(line)
                if rec["seq"] > after_seq:
                    out.append(rec)
                    if len(out) >= limit:
                        break
        return out

    async def sse_stream(self, stream_id: str, last_event_id: str | None = None):
        """Async generator yielding SSE-formatted frames. Heartbeats every
        HEARTBEAT_SECONDS; replays from Last-Event-ID without duplicates."""
        after = 0
        if last_event_id and last_event_id.startswith("evt_"):
            try:
                after = int(last_event_id.removeprefix("evt_"))
            except ValueError:
                after = 0
        last_beat = asyncio.get_event_loop().time()
        while True:
            records = self.read_since(stream_id, after_seq=after, limit=100)
            for rec in records:
                after = rec["seq"]
                yield f"id: {rec['id']}\nevent: {rec['event']}\ndata: {json.dumps(rec, sort_keys=True)}\n\n"
                last_beat = asyncio.get_event_loop().time()
            now = asyncio.get_event_loop().time()
            if now - last_beat >= HEARTBEAT_SECONDS:
                yield f"event: heartbeat\ndata: {{\"at\": \"{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}\"}}\n\n"
                last_beat = now
            await asyncio.sleep(1.0)


def atomic_write_json(path: Path, doc: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(doc, f, sort_keys=True)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
