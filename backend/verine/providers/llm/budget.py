"""LLM budgets and request-rate limits. Blocks calls before spend, never after.

Defaults (env-overridable): auto-analysis OFF, 30 requests/hour, 500 cents/day.
Spend estimates use provider cost metadata when available; unknown costs count
against the request limit but are recorded as cost_unknown."""

from __future__ import annotations

import os
from datetime import datetime, timezone

from ...common.errors import VerineError
from ...api.repositories import FileStore

COLLECTION = "llm_budget"


class BudgetExceeded(VerineError):
    error_code = "LLM_BUDGET_EXCEEDED"


class BudgetTracker:
    def __init__(self, store: FileStore):
        self.store = store

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def _doc(self) -> dict:
        day = self._now().strftime("%Y-%m-%d")
        doc_id = f"budget_{day}"
        if self.store.exists(COLLECTION, doc_id):
            return self.store.get(COLLECTION, doc_id)
        return {"id": doc_id, "day": day, "spent_cents": 0.0, "requests": [], "cost_unknown_requests": 0}

    def check_and_reserve(self, estimated_cost_cents: float | None) -> None:
        doc = self._doc()
        max_per_hour = int(os.environ.get("VERINE_LLM_REQUESTS_PER_HOUR", "30"))
        daily_budget = int(os.environ.get("VERINE_LLM_DAILY_BUDGET_CENTS", "500"))

        hour_ago = self._now().timestamp() - 3600
        recent = [t for t in doc["requests"] if t > hour_ago]
        if len(recent) >= max_per_hour:
            raise BudgetExceeded(f"Request limit reached: {max_per_hour}/hour")
        if estimated_cost_cents is not None and doc["spent_cents"] + estimated_cost_cents > daily_budget:
            raise BudgetExceeded(
                f"Daily budget would be exceeded: spent {doc['spent_cents']:.1f}c "
                f"+ est {estimated_cost_cents:.1f}c > {daily_budget}c"
            )

        doc["requests"] = recent + [self._now().timestamp()]
        self.store.put(COLLECTION, doc["id"], doc)

    def record_spend(self, cost_cents: float | None) -> None:
        doc = self._doc()
        if cost_cents is None:
            doc["cost_unknown_requests"] += 1
        else:
            doc["spent_cents"] += cost_cents
        self.store.put(COLLECTION, doc["id"], doc)

    def status(self) -> dict:
        doc = self._doc()
        return {
            "day": doc["day"],
            "spent_cents": round(doc["spent_cents"], 2),
            "daily_budget_cents": int(os.environ.get("VERINE_LLM_DAILY_BUDGET_CENTS", "500")),
            "requests_last_hour": len(
                [t for t in doc["requests"] if t > self._now().timestamp() - 3600]
            ),
            "requests_per_hour_limit": int(os.environ.get("VERINE_LLM_REQUESTS_PER_HOUR", "30")),
            "cost_unknown_requests": doc["cost_unknown_requests"],
            "auto_analysis": os.environ.get("VERINE_LLM_AUTO_ANALYSIS", "0") == "1",
        }
