"""API routers implementing the v0.1 endpoint contract."""

from __future__ import annotations

import subprocess
from pathlib import Path

from fastapi import APIRouter, Query
from pydantic import BaseModel, ConfigDict, Field

from .. import __version__
from ..capabilities.schema import Capability
from ..common.errors import NotFoundError
from ..graph.edges import Edge
from ..graph.nodes import Node
from ..graph.snapshots import GraphSnapshot
from ..incidents.schema import Incident
from ..optimization.exhaustive import OptimizerWeights
from ..simulation.scenarios import ScenarioConstraints, ScheduledAction
from .repositories import Repositories
from .service import get_service

router = APIRouter(prefix="/api")


def _git_commit() -> str:
    try:
        return (
            subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                capture_output=True, text=True, cwd=Path(__file__).parent, timeout=3,
            ).stdout.strip()
            or "unknown"
        )
    except Exception:
        return "unknown"


_COMMIT = None


@router.get("/health")
def health() -> dict:
    global _COMMIT
    if _COMMIT is None:
        _COMMIT = _git_commit()
    return {
        "status": "ok",
        "version": __version__,
        "commit": _COMMIT,
        "mode": "synthetic_fixture",
        "disclaimer": "Synthetic simulation prototype; results are not real-world forecasts.",
    }


# ------------------------------------------------------------- capabilities
@router.get("/capabilities")
def list_capabilities() -> list[dict]:
    svc = get_service()
    return svc.repos.store.list_all(Repositories.CAPABILITIES)


@router.post("/capabilities", status_code=201)
def create_capability(capability: Capability) -> dict:
    svc = get_service()
    svc.repos.store.put(Repositories.CAPABILITIES, capability.capability_id, capability.model_dump(mode="json"))
    return capability.model_dump(mode="json")


@router.get("/capabilities/{cap_id}")
def get_capability(cap_id: str) -> dict:
    svc = get_service()
    cap = svc.get_capability(cap_id)
    meta = svc.fixture_meta()
    snapshot = svc.get_snapshot(meta["graph_snapshot_id"])
    dependencies = [e.model_dump(mode="json") for e in snapshot.edges if e.from_node == cap_id]
    return {"capability": cap.model_dump(mode="json"), "dependencies": dependencies}


# ---------------------------------------------------------------- snapshots
class SnapshotIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    graph_snapshot_id: str
    version: str = "v1"
    capabilities: list[Capability]
    nodes: list[Node]
    edges: list[Edge]


@router.post("/graph/snapshots", status_code=201)
def create_snapshot(body: SnapshotIn) -> dict:
    svc = get_service()
    snapshot = GraphSnapshot(**body.model_dump())
    return svc.store_snapshot(snapshot)


@router.get("/graph/snapshots/{snapshot_id}")
def get_snapshot(snapshot_id: str) -> dict:
    return get_service().repos.get_snapshot(snapshot_id)


# ---------------------------------------------------------------- incidents
@router.get("/incidents")
def list_incidents() -> list[dict]:
    return get_service().repos.store.list_all(Repositories.INCIDENTS)


@router.post("/incidents", status_code=201)
def create_incident(incident: Incident) -> dict:
    svc = get_service()
    meta = svc.fixture_meta()
    snapshot = svc.get_snapshot(meta["graph_snapshot_id"])
    node_ids = snapshot.all_node_ids()
    from ..common.errors import ScenarioInvalidError

    bad = [c.target_node_id for c in incident.components if c.target_node_id not in node_ids]
    if bad:
        raise ScenarioInvalidError(
            "Incident targets unknown nodes",
            field_errors=[{"field": "components", "reason": f"Unknown node {b}"} for b in bad],
        )
    svc.repos.store.put(Repositories.INCIDENTS, incident.incident_id, incident.model_dump(mode="json"))
    return incident.model_dump(mode="json")


@router.get("/incidents/{incident_id}")
def get_incident(incident_id: str) -> dict:
    return get_service().repos.store.get(Repositories.INCIDENTS, incident_id)


# ------------------------------------------------------------------ actions
@router.get("/actions")
def list_actions() -> list[dict]:
    return get_service().repos.store.list_all(Repositories.ACTIONS)


# ------------------------------------------------------------------ presets
@router.get("/presets")
def presets() -> dict:
    return get_service().fixture_meta()


# ---------------------------------------------------------------- scenarios
class ScenarioCompileIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    capability_id: str
    incident_id: str
    graph_snapshot_id: str | None = None
    constraints: ScenarioConstraints | None = None
    hidden_edge_ids: list[str] = Field(default_factory=list)
    scheduled_actions: list[ScheduledAction] = Field(default_factory=list)
    seed: int | None = None
    horizon_minutes: int = Field(default=720, gt=0, le=10080)
    monte_carlo_replications: int = Field(default=100, gt=0, le=500)
    model_set: list[str] | None = None


@router.get("/scenarios")
def list_scenarios() -> list[dict]:
    return get_service().repos.store.list_all(Repositories.SCENARIOS)


@router.post("/scenarios/compile", status_code=201)
def compile_scenario_endpoint(body: ScenarioCompileIn) -> dict:
    svc = get_service()
    scenario, compiled = svc.compile_and_store_scenario(
        capability_id=body.capability_id,
        incident_id=body.incident_id,
        graph_snapshot_id=body.graph_snapshot_id,
        constraints=body.constraints,
        hidden_edge_ids=body.hidden_edge_ids,
        scheduled_actions=body.scheduled_actions,
        seed=body.seed,
        horizon_minutes=body.horizon_minutes,
        monte_carlo_replications=body.monte_carlo_replications,
        model_set=body.model_set,
    )
    return {
        "scenario": scenario.model_dump(mode="json"),
        "scenario_hash": compiled.scenario_hash,
        "graph_hash": compiled.graph_hash,
        "warnings": compiled.warnings,
    }


@router.get("/scenarios/{scenario_id}")
def get_scenario(scenario_id: str) -> dict:
    return get_service().repos.store.get(Repositories.SCENARIOS, scenario_id)


# -------------------------------------------------------------- simulations
class SimulationRunIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scenario_id: str
    weights: OptimizerWeights | None = None


@router.post("/simulations/run", status_code=201)
def run_simulation(body: SimulationRunIn) -> dict:
    svc = get_service()
    result = svc.run_simulation(body.scenario_id, body.weights)
    return {
        "run_id": result["run_id"],
        "run_hash": result["run_hash"],
        "model_outputs": result["model_outputs"],
        "comparables": result["comparables"],
        "disagreement": result["disagreement"],
        "unknowns": result["unknowns"],
        "containment": result["containment"],
        "case_file": result["case_file"],
        "warnings": result["warnings"],
    }


@router.get("/simulations/{run_id}")
def get_simulation(run_id: str) -> dict:
    return get_service().repos.store.get(Repositories.RUNS, run_id)


# -------------------------------------------------------------- containment
class OptimizeIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scenario_id: str
    weights: OptimizerWeights | None = None
    constraints_override: ScenarioConstraints | None = None


@router.post("/containment/optimize")
def optimize(body: OptimizeIn) -> dict:
    return get_service().optimize(body.scenario_id, body.weights, body.constraints_override)


# -------------------------------------------------------------------- cases
@router.get("/cases")
def list_cases() -> list[dict]:
    svc = get_service()
    out = []
    for doc in svc.repos.store.list_all(Repositories.CASES):
        c = doc["case_json"]
        out.append(
            {
                "case_file_id": doc["id"],
                "scenario_id": doc["scenario_id"],
                "case_type": doc["case_type"],
                "capability_status": c.get("capability_status"),
                "executed_at": c.get("executed_at"),
                "run_hash": c.get("run_hash"),
            }
        )
    return out


class CaseSaveIn(BaseModel):
    model_config = ConfigDict(extra="allow")
    case_file_id: str
    scenario_id: str


@router.post("/cases", status_code=201)
def save_case(body: CaseSaveIn) -> dict:
    from ..cases.schema import CaseFile
    from ..common.hashing import hash_obj

    svc = get_service()
    case = CaseFile(**body.model_dump())
    doc = case.model_dump(mode="json")
    svc.repos.store.put(
        Repositories.CASES,
        case.case_file_id,
        {"id": case.case_file_id, "scenario_id": case.scenario_id, "case_type": case.case_type,
         "case_json": doc, "case_hash": hash_obj(doc)},
    )
    return {"case_file_id": case.case_file_id}


@router.get("/cases/{case_id}")
def get_case(case_id: str) -> dict:
    return get_service().repos.store.get(Repositories.CASES, case_id)


@router.post("/cases/{case_id}/replay")
def replay_case_endpoint(case_id: str) -> dict:
    return get_service().replay(case_id)


# ----------------------------------------------------------------- evidence
@router.get("/evidence")
def list_evidence(epistemic_status: str | None = Query(default=None)) -> dict:
    svc = get_service()
    evidence = svc.repos.store.list_all(Repositories.EVIDENCE)
    assumptions = svc.repos.store.list_all(Repositories.ASSUMPTIONS)
    if epistemic_status:
        evidence = [e for e in evidence if e.get("epistemic_status") == epistemic_status]
        assumptions = [a for a in assumptions if a.get("epistemic_status") == epistemic_status]
    return {"evidence": evidence, "assumptions": assumptions}


@router.get("/evidence/{evidence_id}")
def get_evidence(evidence_id: str) -> dict:
    svc = get_service()
    store = svc.repos.store
    if store.exists(Repositories.EVIDENCE, evidence_id):
        return store.get(Repositories.EVIDENCE, evidence_id)
    if store.exists(Repositories.ASSUMPTIONS, evidence_id):
        return store.get(Repositories.ASSUMPTIONS, evidence_id)
    raise NotFoundError(f"evidence/{evidence_id} not found")


# -------------------------------------------------------------- experiments
@router.get("/experiments")
def list_experiments() -> dict:
    import json

    root = Path(__file__).resolve().parents[3] / "research"
    registry_path = root / "experiments" / "registry.json"
    registry = json.loads(registry_path.read_text()) if registry_path.exists() else {"experiments": []}
    benchmarks = {}
    bench_dir = root / "benchmark"
    if bench_dir.exists():
        for p in sorted(bench_dir.glob("*.json")):
            benchmarks[p.stem] = json.loads(p.read_text())
    return {"registry": registry, "benchmarks": benchmarks}
