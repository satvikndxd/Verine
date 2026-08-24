"""Fixture loading: parse the demo fixture into validated domain objects."""

from __future__ import annotations

import json
from pathlib import Path

from .capabilities.schema import Capability
from .evidence.schema import Evidence
from .graph.edges import Edge
from .graph.nodes import Node
from .graph.snapshots import GraphSnapshot
from .graph.validate import validate_graph
from .incidents.schema import Incident
from .optimization.actions import Action
from .simulation.scenarios import ScenarioConstraints

MAX_FIXTURE_BYTES = 5 * 1024 * 1024  # reject oversized payloads


def default_fixture_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "fixtures"


class FixtureBundle:
    def __init__(self, raw: dict):
        self.fixture_id: str = raw["fixture_id"]
        capability = Capability(**raw["capability"])
        self.snapshot = GraphSnapshot(
            graph_snapshot_id=raw["graph_snapshot_id"],
            capabilities=[capability],
            nodes=[Node(**n) for n in raw["nodes"]],
            edges=[Edge(**e) for e in raw["edges"]],
        )
        self.actions = [Action(**a) for a in raw["actions"]]
        self.incidents = {i["incident_id"]: Incident(**i) for i in raw["incidents"]}
        self.scenario_presets = raw.get("scenario_presets", [])
        self.default_constraints = ScenarioConstraints(**raw["default_constraints"])
        self.default_seed: int = raw["default_seed"]
        self.warnings = validate_graph(self.snapshot)

    @property
    def capability(self) -> Capability:
        return self.snapshot.capabilities[0]


def load_fixture(path: Path | None = None) -> FixtureBundle:
    path = path or default_fixture_dir() / "digital_payments_capability.json"
    if path.stat().st_size > MAX_FIXTURE_BYTES:
        raise ValueError("Fixture exceeds size limit")
    raw = json.loads(path.read_text())
    return FixtureBundle(raw)


def load_evidence(path: Path | None = None) -> list[Evidence]:
    path = path or default_fixture_dir() / "evidence.json"
    raw = json.loads(path.read_text())
    return [Evidence(**e) for e in raw["evidence"]]
