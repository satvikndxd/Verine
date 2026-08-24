"""Common metric helpers shared by models and benchmarks."""

from __future__ import annotations


def service_loss_sl_hours(service_levels: list[float], target: float, step_minutes: int) -> float:
    return round(sum(max(0.0, target - sl) for sl in service_levels) * step_minutes / 60.0, 6)


def affected_precision_recall(predicted: set[str], truth: set[str]) -> dict:
    tp = len(predicted & truth)
    precision = tp / len(predicted) if predicted else 1.0 if not truth else 0.0
    recall = tp / len(truth) if truth else 1.0
    return {
        "precision": round(precision, 6),
        "recall": round(recall, 6),
        "true_positives": tp,
        "false_positives": sorted(predicted - truth),
        "false_negatives": sorted(truth - predicted),
    }


def normalized_diff(a: float | None, b: float | None, scale: float) -> float | None:
    """|a-b| / scale, with None handled explicitly (None vs value = 1.0 = maximal)."""
    if a is None and b is None:
        return 0.0
    if a is None or b is None:
        return 1.0
    if scale <= 0:
        return 0.0
    return round(min(1.0, abs(a - b) / scale), 6)
