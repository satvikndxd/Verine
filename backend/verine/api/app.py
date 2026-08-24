"""FastAPI app factory."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .errors import install_error_handlers
from .routes import router
from .service import init_service


def create_app(data_dir: Path | None = None, fixture_dir: Path | None = None) -> FastAPI:
    app = FastAPI(
        title="VERINE NERVE API",
        version="0.1.0",
        description=(
            "Capability-level crisis compiler (synthetic prototype). "
            "All simulation outputs are model results over synthetic fixtures, "
            "not predictions about real organizations."
        ),
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    install_error_handlers(app)

    data_dir = data_dir or Path(os.environ.get("VERINE_DATA_DIR", Path(__file__).resolve().parents[3] / "data"))
    init_service(data_dir, fixture_dir)

    app.include_router(router)
    return app
