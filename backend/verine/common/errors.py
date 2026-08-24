"""Structured domain errors."""

from __future__ import annotations

from typing import Any


class VerineError(Exception):
    error_code = "VERINE_ERROR"

    def __init__(self, message: str, field_errors: list[dict[str, Any]] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.field_errors = field_errors or []

    def to_dict(self, request_id: str = "req_local") -> dict[str, Any]:
        return {
            "error_code": self.error_code,
            "message": self.message,
            "field_errors": self.field_errors,
            "request_id": request_id,
        }


class GraphInvalidError(VerineError):
    error_code = "GRAPH_INVALID"


class ScenarioInvalidError(VerineError):
    error_code = "SCENARIO_INVALID"


class NotFoundError(VerineError):
    error_code = "NOT_FOUND"


class ConflictError(VerineError):
    error_code = "CONFLICT"


class ConstraintViolationError(VerineError):
    error_code = "CONSTRAINT_VIOLATION"
