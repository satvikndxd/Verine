"""Structured API error contract: code, message, field errors, request id."""

from __future__ import annotations

import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from ..common.errors import ConflictError, NotFoundError, VerineError


def _request_id() -> str:
    return "req_" + uuid.uuid4().hex[:12]


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(VerineError)
    async def verine_error(_: Request, exc: VerineError):
        status = 404 if isinstance(exc, NotFoundError) else 409 if isinstance(exc, ConflictError) else 422
        return JSONResponse(status_code=status, content=exc.to_dict(_request_id()))

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError):
        field_errors = [
            {"field": ".".join(str(p) for p in e.get("loc", [])), "reason": e.get("msg", "invalid")}
            for e in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content={
                "error_code": "VALIDATION_ERROR",
                "message": "Request failed validation",
                "field_errors": field_errors,
                "request_id": _request_id(),
            },
        )
