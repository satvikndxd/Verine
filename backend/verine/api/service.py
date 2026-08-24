"""Application service layer shared by the API routers and the CLI."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from ..capabilities.schema import Capability
from ..cases.replay import replay_case
from ..cases.runner import execute_scenario
from ..cases.schema import CaseFile
from ..common.errors import NotFoundError
from ..common.hashing import hash_obj
from ..common.ids import derived_id
from ..fixtures import FixtureBundle, default_fixture_dir, load_fixture
from ..graph.edges import Edge
from ..graph.nodes import Node
from ..graph.snapshots import GraphSnapshot
from ..graph.validate import validate_graph
from ..incidents.schema import Incident
from ..optimization.actions import Action
from ..optimization.exhaustive import OptimizerWeights, optimize_containment
from ..simulation.compiler import CompiledScenario, compile_scenario
from ..simulation.scenarios import Scenario, ScenarioConstraints, ScheduledAction
from .repositories import FileStore, Repositories


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class VerineService:
    def __init__(self, data_dir: Path, fixture_dir: Path | None = None):
        self.repos = Repositories(FileStore(data_dir))
        self.fixture_dir = fixture_dir or default_fixture_dir()

    # ------------------------------------------------------------------ seed
    def seed_fixture(self) -> FixtureBundle:
        bundle = load_fixture(self.fixture_dir / "digital_payments_capability.json")
        r = self.repos

        cap = bundle.capability
        r.store.put(r.CAPABILITIES, cap.capability_id, cap.model_dump(mode="json"))
        snapshot_doc = bundle.snapshot.model_dump(mode="json")
        r.put_snapshot(snapshot_doc, bundle.snapshot.graph_hash(), bundle.snapshot.epistemic_summary())
        for inc in bundle.incidents.values():
            r.store.put(r.INCIDENTS, inc.incident_id, inc.model_dump(mode="json"))
        for a in bundle.actions:
            r.store.put(r.ACTIONS, a.action_id, a.model_dump(mode="json"))

        ev_path = self.fixture_dir / "evidence.json"
        if ev_path.exists():
            raw = json.loads(ev_path.read_text())
            for e in raw.get("evidence", []):
                r.store.put(r.EVIDENCE, e["evidence_id"], e)
            for a in raw.get("assumptions", []):
                r.store.put(r.ASSUMPTIONS, a["assumption_id"], a)

        r.store.put(
            "meta",
            "fixture",
            {
                "fixture_id": bundle.fixture_id,
                "graph_snapshot_id": bundle.snapshot.graph_snapshot_id,
                "scenario_presets": bundle.scenario_presets,
                "default_constraints": bundle.default_constraints.model_dump(mode="json"),
                "default_seed": bundle.default_seed,
                "graph_warnings": bundle.warnings,
            },
        )
        return bundle

    def fixture_meta(self) -> dict:
        return self.repos.store.get("meta", "fixture")

    # ------------------------------------------------------------- accessors
    def get_capability(self, cap_id: str) -> Capability:
        return Capability(**self.repos.store.get(Repositories.CAPABILITIES, cap_id))

    def get_snapshot(self, snapshot_id: str) -> GraphSnapshot:
        doc = self.repos.get_snapshot(snapshot_id)
        g = doc["graph_json"]
        return GraphSnapshot(
            graph_snapshot_id=g["graph_snapshot_id"],
            version=g.get("version", "v1"),
            capabilities=[Capability(**c) for c in g["capabilities"]],
            nodes=[Node(**n) for n in g["nodes"]],
            edges=[Edge(**e) for e in g["edges"]],
        )

    def get_incident(self, incident_id: str) -> Incident:
        return Incident(**self.repos.store.get(Repositories.INCIDENTS, incident_id))

    def list_actions(self) -> list[Action]:
        return [Action(**a) for a in self.repos.store.list_all(Repositories.ACTIONS)]

    def get_scenario(self, scenario_id: str) -> Scenario:
        return Scenario(**self.repos.store.get(Repositories.SCENARIOS, scenario_id)["scenario_json"])

    # ------------------------------------------------------------- workflows
    def store_snapshot(self, snapshot: GraphSnapshot) -> dict:
        warnings = validate_graph(snapshot)
        self.repos.put_snapshot(
            snapshot.model_dump(mode="json"), snapshot.graph_hash(), snapshot.epistemic_summary()
        )
        return {"graph_snapshot_id": snapshot.graph_snapshot_id, "graph_hash": snapshot.graph_hash(), "warnings": warnings}

    def compile_and_store_scenario(
        self,
        capability_id: str,
        incident_id: str,
        graph_snapshot_id: str | None = None,
        constraints: ScenarioConstraints | None = None,
        hidden_edge_ids: list[str] | None = None,
        scheduled_actions: list[ScheduledAction] | None = None,
        seed: int | None = None,
        horizon_minutes: int = 720,
        monte_carlo_replications: int = 100,
        model_set: list[str] | None = None,
    ) -> tuple[Scenario, CompiledScenario]:
        meta = self.fixture_meta()
        graph_snapshot_id = graph_snapshot_id or meta["graph_snapshot_id"]
        constraints = constraints or ScenarioConstraints(**meta["default_constraints"])
        seed = seed if seed is not None else meta["default_seed"]
        model_set = model_set or [
            "reachability_v1",
            "deterministic_propagation_v1",
            "capacity_flow_v1",
            "monte_carlo_v1",
        ]
        body = {
            "capability_id": capability_id,
            "graph_snapshot_id": graph_snapshot_id,
            "incident_id": incident_id,
            "constraints": constraints.model_dump(mode="json"),
            "scheduled_actions": [s.model_dump(mode="json") for s in (scheduled_actions or [])],
            "hidden_edge_ids": hidden_edge_ids or [],
            "seed": seed,
            "horizon_minutes": horizon_minutes,
            "monte_carlo_replications": monte_carlo_replications,
            "model_set": model_set,
        }
        scenario = Scenario(
            scenario_id=derived_id("scenario", body), created_at=now_utc(), **body
        )
        compiled = compile_scenario(
            scenario, self.get_snapshot(graph_snapshot_id), self.get_incident(incident_id), self.list_actions()
        )
        self.repos.store.put(
            Repositories.SCENARIOS,
            scenario.scenario_id,
            {
                "id": scenario.scenario_id,
                "capability_id": capability_id,
                "graph_snapshot_id": graph_snapshot_id,
                "incident_id": incident_id,
                "scenario_hash": compiled.scenario_hash,
                "scenario_json": scenario.model_dump(mode="json"),
            },
        )
        return scenario, compiled

    def compiled_from_stored(self, scenario_id: str) -> CompiledScenario:
        scenario = self.get_scenario(scenario_id)
        return compile_scenario(
            scenario,
            self.get_snapshot(scenario.graph_snapshot_id),
            self.get_incident(scenario.incident_id),
            self.list_actions(),
        )

    def run_simulation(self, scenario_id: str, weights: OptimizerWeights | None = None) -> dict:
        compiled = self.compiled_from_stored(scenario_id)
        started = now_utc()
        result = execute_scenario(compiled, self.list_actions(), weights=weights, executed_at=started)
        case: CaseFile = result["case_file"]
        run_id = derived_id("run", {"scenario": compiled.scenario_hash, "run": result["run_hash"]})
        self.repos.store.put(
            Repositories.RUNS,
            run_id,
            {
                "id": run_id,
                "scenario_id": scenario_id,
                "model_id": ",".join(compiled.scenario.model_set),
                "seed": compiled.scenario.seed,
                "result_json": {
                    "model_outputs": result["model_outputs"],
                    "comparables": result["comparables"],
                    "disagreement": result["disagreement"],
                    "unknowns": result["unknowns"],
                    "containment": result["containment"],
                },
                "run_hash": result["run_hash"],
                "status": "completed",
                "started_at": started,
                "completed_at": now_utc(),
            },
        )
        case_doc = case.model_dump(mode="json")
        self.repos.store.put(
            Repositories.CASES,
            case.case_file_id,
            {
                "id": case.case_file_id,
                "scenario_id": scenario_id,
                "case_type": case.case_type,
                "case_json": case_doc,
                "case_hash": hash_obj(case_doc),
            },
        )
        return {"run_id": run_id, **result, "case_file": case_doc}

    def replay(self, case_id: str) -> dict:
        case_doc = self.repos.store.get(Repositories.CASES, case_id)
        case = CaseFile(**case_doc["case_json"])
        compiled = self.compiled_from_stored(case_doc["scenario_id"])
        return replay_case(case, compiled, self.list_actions())

    def optimize(self, scenario_id: str, weights: OptimizerWeights | None,
                 constraints_override: ScenarioConstraints | None) -> dict:
        compiled = self.compiled_from_stored(scenario_id)
        if constraints_override is not None:
            compiled.scenario.constraints = constraints_override
        return optimize_containment(compiled, self.list_actions(), weights)


_service: VerineService | None = None


def get_service() -> VerineService:
    global _service
    if _service is None:
        raise NotFoundError("Service not initialized")
    return _service


def init_service(data_dir: Path, fixture_dir: Path | None = None) -> VerineService:
    global _service
    _service = VerineService(data_dir, fixture_dir)
    _service.seed_fixture()
    return _service
