"""UTC time utilities and interval validation. No wall-clock reads in simulation."""

from __future__ import annotations

from datetime import datetime, timezone


def parse_utc(value: str) -> datetime:
    """Parse an ISO-8601 timestamp; must be timezone-aware, normalized to UTC."""
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError(f"Timestamp {value!r} must be timezone-aware")
    return dt.astimezone(timezone.utc)


def to_utc_iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        raise ValueError("Naive datetime not allowed")
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def validate_interval(low: float, median: float, high: float) -> None:
    if not (low <= median <= high):
        raise ValueError(f"Interval must satisfy low<=median<=high, got {low}, {median}, {high}")
