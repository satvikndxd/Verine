"""Delta engine: suppress duplicate unchanged signals via cursor state.

A signal is NEW if its source_event_id is unseen, UPDATED if the normalized
hash changed, and suppressed otherwise."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..providers.live.base import ConnectorCursor
from .schema import ExternalSignal


@dataclass
class DeltaResult:
    new: list[ExternalSignal] = field(default_factory=list)
    updated: list[ExternalSignal] = field(default_factory=list)
    suppressed: int = 0


def apply_delta(signals: list[ExternalSignal], cursor: ConnectorCursor) -> DeltaResult:
    result = DeltaResult()
    for s in signals:
        prev = cursor.seen.get(s.source_event_id)
        if prev is None:
            result.new.append(s)
            cursor.seen[s.source_event_id] = s.normalized_hash
        elif prev != s.normalized_hash:
            result.updated.append(s)
            cursor.seen[s.source_event_id] = s.normalized_hash
        else:
            result.suppressed += 1
    # Bound cursor growth deterministically (keep most recent 500 by insertion).
    if len(cursor.seen) > 500:
        for key in list(cursor.seen)[: len(cursor.seen) - 500]:
            del cursor.seen[key]
    return result
