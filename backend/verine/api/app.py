"""FastAPI app factory."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .errors import install_error_handlers
from .live_service import init_live_service
from .routes import router
from .service import init_service
from .verine_routes import router as verine_router


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
    sim = init_service(data_dir, fixture_dir)
    live = init_live_service(sim, Path(data_dir) / "verine")
    seed_verine_fixtures(live, sim, fixture_dir)

    app.include_router(router)
    app.include_router(verine_router)
    return app


def seed_verine_fixtures(live, sim, fixture_dir: Path | None) -> None:
    """Seed offline connectors and the Digital Payments watch pack so the
    live war room works with no network and no manual setup."""
    import json

    from ..fixtures import default_fixture_dir
    from ..graph.watch_packs import WatchPack
    from ..providers.live.base import ConnectorConfig

    fdir = Path(fixture_dir) if fixture_dir else default_fixture_dir()
    live_dir = fdir / "live"
    meta = sim.fixture_meta()
    snapshot_id = meta["graph_snapshot_id"]

    connectors = [
        ("conn_statuspage_demo", "statuspage", "processor_status.json", "strong", "acme_processor"),
        ("conn_cisa_demo", "cisa_kev", "cisa_kev.json", "strong", "cisa"),
        ("conn_nws_demo", "nws", "nws_alerts.json", "weak", "nws"),
    ]
    for cid, ctype, fixture_file, strength, group in connectors:
        if live.store.exists("connectors", cid):
            continue
        fixture_path = live_dir / fixture_file
        if not fixture_path.exists():
            continue
        live.create_connector(ConnectorConfig(
            connector_id=cid,
            connector_type=ctype,
            label=f"{ctype} (offline fixture)",
            fixture_path=str(fixture_path),
            enabled=True,
            source_strength=strength,
            source_independence_group=group,
            params={"match_terms": ["acme", "payment"]} if ctype == "cisa_kev" else {},
        ))

    wp_id = "wp_digital_payments"
    if not live.store.exists("watch_packs", wp_id):
        aliases_path = live_dir / "watch_pack_aliases.json"
        aliases = json.loads(aliases_path.read_text()) if aliases_path.exists() else {}
        live.create_watch_pack(WatchPack(
            watch_pack_id=wp_id,
            name="Digital Payments Authorization",
            capability_id="cap_digital_payments_authorization",
            graph_snapshot_id=snapshot_id,
            connector_ids=[c[0] for c in connectors if live.store.exists("connectors", c[0])],
            aliases=aliases.get("aliases", {}),
            geographies=aliases.get("geographies", []),
            auto_analysis=True,
        ))
