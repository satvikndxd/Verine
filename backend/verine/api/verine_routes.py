"""VERINE live-intelligence router (/api/verine namespace).

Layered on top of the existing synthetic kernel. No endpoint turns external
evidence into confirmed internal impact; hypothesis confirmation requires an
explicit actor + reason."""

from __future__ import annotations

from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from ..common.errors import VerineError
from ..graph.watch_packs import WatchPack
from ..providers.live.base import ConnectorConfig
from ..providers.registry import provider_catalog
from ..vault.contracts import CredentialCreate
from .live_service import get_live_service
from .service import get_service

router = APIRouter(prefix="/api/verine")


# ------------------------------------------------------------- providers/creds
@router.get("/providers")
def list_providers() -> list[dict]:
    return provider_catalog()


@router.get("/providers/{provider_id}/models")
async def provider_models(provider_id: str, credential_id: str | None = Query(default=None)) -> dict:
    from ..providers.registry import llm_provider

    live = get_live_service()
    api_key = None
    base_url = None
    if credential_id:
        cred = live.vault.get(credential_id)
        api_key = live.vault.decrypt_key(credential_id)
        base_url = cred.base_url
    provider = llm_provider(provider_id, transport=live._llm_transport)
    models = await provider.list_models(api_key, base_url)
    return {"provider_id": provider_id, "models": [m.model_dump(mode="json") for m in models]}


@router.get("/credentials")
def list_credentials() -> list[dict]:
    return [c.model_dump(mode="json") for c in get_live_service().vault.list_meta()]


@router.post("/credentials", status_code=201)
def create_credential(body: CredentialCreate) -> dict:
    return get_live_service().vault.create(body).model_dump(mode="json")


@router.post("/credentials/{cred_id}/test")
async def test_credential(cred_id: str) -> dict:
    from ..providers.registry import llm_provider

    live = get_live_service()
    cred = live.vault.get(cred_id)
    api_key = live.vault.decrypt_key(cred_id)
    provider = llm_provider(cred.provider_id, transport=live._llm_transport)
    health = await provider.health_check(api_key, cred.base_url)
    meta = live.vault.record_test(cred_id, health.status)
    return {"health": health.model_dump(mode="json"), "credential": meta.model_dump(mode="json")}


class CredentialPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: str | None = None
    enabled: bool | None = None
    usage_budget_cents: int | None = None
    default_model: str | None = None
    api_key: str | None = None


@router.patch("/credentials/{cred_id}")
def patch_credential(cred_id: str, body: CredentialPatch) -> dict:
    patch = {k: v for k, v in body.model_dump().items() if v is not None}
    return get_live_service().vault.update(cred_id, patch).model_dump(mode="json")


@router.delete("/credentials/{cred_id}", status_code=204)
def delete_credential(cred_id: str) -> None:
    get_live_service().vault.delete(cred_id)


# -------------------------------------------------------------------- connectors
@router.get("/connectors")
def list_connectors() -> list[dict]:
    return [c.model_dump(mode="json") for c in get_live_service().list_connectors()]


@router.post("/connectors", status_code=201)
def create_connector(config: ConnectorConfig) -> dict:
    return get_live_service().create_connector(config).model_dump(mode="json")


@router.get("/connectors/{connector_id}")
def get_connector(connector_id: str) -> dict:
    return get_live_service().get_connector(connector_id).model_dump(mode="json")


class ConnectorPatch(BaseModel):
    model_config = ConfigDict(extra="allow")


@router.patch("/connectors/{connector_id}")
def patch_connector(connector_id: str, body: ConnectorPatch) -> dict:
    return get_live_service().patch_connector(connector_id, body.model_dump()).model_dump(mode="json")


@router.post("/connectors/{connector_id}/health")
async def connector_health(connector_id: str) -> dict:
    return await get_live_service().connector_health(connector_id)


class PollBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    watch_pack_id: str | None = None


@router.post("/connectors/{connector_id}/poll")
async def poll_connector(connector_id: str, body: PollBody | None = None) -> dict:
    wp = body.watch_pack_id if body else None
    return await get_live_service().poll_connector(connector_id, wp)


@router.post("/connectors/{connector_id}/enable")
def enable_connector(connector_id: str) -> dict:
    return get_live_service().patch_connector(connector_id, {"enabled": True}).model_dump(mode="json")


@router.post("/connectors/{connector_id}/disable")
def disable_connector(connector_id: str) -> dict:
    return get_live_service().patch_connector(connector_id, {"enabled": False}).model_dump(mode="json")


# ------------------------------------------------------------------- watch packs
@router.get("/watch-packs")
def list_watch_packs() -> list[dict]:
    return [w.model_dump(mode="json") for w in get_live_service().list_watch_packs()]


@router.post("/watch-packs", status_code=201)
def create_watch_pack(pack: WatchPack) -> dict:
    return get_live_service().create_watch_pack(pack).model_dump(mode="json")


@router.get("/watch-packs/{watch_pack_id}")
def get_watch_pack(watch_pack_id: str) -> dict:
    return get_live_service().get_watch_pack(watch_pack_id).model_dump(mode="json")


@router.post("/watch-packs/{watch_pack_id}/start")
async def start_watch_pack(watch_pack_id: str) -> dict:
    return await get_live_service().start_watch_pack(watch_pack_id)


@router.post("/watch-packs/{watch_pack_id}/pause")
def pause_watch_pack(watch_pack_id: str) -> dict:
    return get_live_service().pause_watch_pack(watch_pack_id)


@router.post("/watch-packs/{watch_pack_id}/poll")
async def poll_watch_pack(watch_pack_id: str) -> dict:
    return await get_live_service().poll_watch_pack(watch_pack_id)


@router.get("/watch-packs/{watch_pack_id}/status")
def watch_pack_status(watch_pack_id: str) -> dict:
    return get_live_service().watch_pack_status(watch_pack_id)


# ---------------------------------------------------------- signals/evidence/hyp
@router.get("/signals")
def list_signals(limit: int = Query(default=100, le=1000)) -> list[dict]:
    live = get_live_service()
    docs = [live.store.get("signals", i) for i in live.store.list_ids("signals")]
    docs.sort(key=lambda s: s.get("published_at", ""), reverse=True)
    return docs[:limit]


@router.get("/signals/{signal_id}")
def get_signal(signal_id: str) -> dict:
    return get_live_service().store.get("signals", signal_id)


@router.get("/evidence")
def list_live_evidence(limit: int = Query(default=200, le=2000)) -> list[dict]:
    live = get_live_service()
    return [live.store.get("live_evidence", i) for i in live.store.list_ids("live_evidence")][:limit]


@router.get("/evidence/{evidence_id}")
def get_live_evidence(evidence_id: str) -> dict:
    return get_live_service().store.get("live_evidence", evidence_id)


@router.get("/shadow-edges")
def list_shadow_edges() -> list[dict]:
    live = get_live_service()
    return [live.store.get("shadow_edges", i) for i in live.store.list_ids("shadow_edges")]


@router.get("/hypotheses")
def list_hypotheses() -> list[dict]:
    return [h.model_dump(mode="json") for h in get_live_service().list_hypotheses()]


@router.get("/hypotheses/{hypothesis_id}")
def get_hypothesis(hypothesis_id: str) -> dict:
    return get_live_service().get_hypothesis(hypothesis_id).model_dump(mode="json")


class HypothesisAction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    actor: str = Field(min_length=1)
    reason: str = Field(min_length=1)


@router.post("/hypotheses/{hypothesis_id}/confirm")
def confirm_hypothesis(hypothesis_id: str, body: HypothesisAction) -> dict:
    return get_live_service().hypothesis_action(
        hypothesis_id, "confirm", body.actor, body.reason
    ).model_dump(mode="json")


@router.post("/hypotheses/{hypothesis_id}/contest")
def contest_hypothesis(hypothesis_id: str, body: HypothesisAction) -> dict:
    return get_live_service().hypothesis_action(
        hypothesis_id, "contest", body.actor, body.reason
    ).model_dump(mode="json")


@router.post("/hypotheses/{hypothesis_id}/resolve")
def resolve_hypothesis(hypothesis_id: str, body: HypothesisAction) -> dict:
    return get_live_service().hypothesis_action(
        hypothesis_id, "resolve", body.actor, body.reason
    ).model_dump(mode="json")


# -------------------------------------------------------------------------- LLM
class LLMCompleteBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    credential_id: str
    model: str
    task: str = "incident_summarize"
    hypothesis_id: str
    watch_pack_id: str | None = None


@router.post("/llm/complete")
async def llm_complete(body: LLMCompleteBody) -> dict:
    return await get_live_service().llm_complete(
        body.credential_id, body.model, body.task, body.hypothesis_id, body.watch_pack_id
    )


@router.get("/llm/budget")
def llm_budget() -> dict:
    return get_live_service().budget.status()


# -------------------------------------------------------------------- forks/cases
class ForkBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action_ids: list[str] = Field(default_factory=list)
    constraints_override: dict | None = None
    watch_pack_id: str | None = None


@router.post("/cases/{case_id}/fork")
def fork_case(case_id: str, body: ForkBody) -> dict:
    return get_live_service().fork_case(
        case_id, body.action_ids, body.constraints_override, body.watch_pack_id
    )


@router.get("/cases/{case_id}/forks")
def list_case_forks(case_id: str) -> list[dict]:
    return get_live_service().list_forks(case_id)


@router.get("/cases/{case_id}/export")
def export_case(case_id: str) -> dict:
    svc = get_service()
    return svc.repos.store.get("case_files", case_id)["case_json"]


# -------------------------------------------------------------------------- SSE
@router.get("/streams/{watch_pack_id}")
async def stream(watch_pack_id: str, request: Request) -> StreamingResponse:
    live = get_live_service()
    last_event_id = request.headers.get("Last-Event-ID")

    async def gen():
        async for frame in live.events.sse_stream(watch_pack_id, last_event_id):
            if await request.is_disconnected():
                break
            yield frame

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.get("/streams/{watch_pack_id}/events")
def stream_events(watch_pack_id: str, after_seq: int = 0, limit: int = Query(default=200, le=1000)) -> dict:
    """Non-SSE polling fallback for the event log (used by tests and simple clients)."""
    return {"events": get_live_service().events.read_since(watch_pack_id, after_seq, limit)}
