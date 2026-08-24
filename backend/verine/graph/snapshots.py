"""Immutable graph snapshots with canonical hashing."""

from __future__ import annotations

from collections import Counter

from pydantic import BaseModel, ConfigDict, Field

from ..capabilities.schema import Capability
from ..common.hashing import hash_obj
from .edges import Edge
from .nodes import Node


class GraphSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    graph_snapshot_id: str
    version: str = "v1"
    capabilities: list[Capability]
    nodes: list[Node]
    edges: list[Edge]

    def canonical_payload(self) -> dict:
        return {
            "version": self.version,
            "capabilities": sorted(
                (c.model_dump(mode="json") for c in self.capabilities), key=lambda c: c["capability_id"]
            ),
            "nodes": sorted((n.model_dump(mode="json") for n in self.nodes), key=lambda n: n["node_id"]),
            "edges": sorted((e.model_dump(mode="json") for e in self.edges), key=lambda e: e["edge_id"]),
        }

    def graph_hash(self) -> str:
        return hash_obj(self.canonical_payload())

    def epistemic_summary(self) -> dict:
        node_counts = Counter(n.epistemic_status.value for n in self.nodes)
        edge_counts = Counter(e.epistemic_status.value for e in self.edges)
        low_conf_edges = [e.edge_id for e in self.edges if e.confidence < 0.7]
        low_obs_nodes = [n.node_id for n in self.nodes if n.observability < 0.6]
        return {
            "node_epistemic_counts": dict(sorted(node_counts.items())),
            "edge_epistemic_counts": dict(sorted(edge_counts.items())),
            "low_confidence_edges": sorted(low_conf_edges),
            "low_observability_nodes": sorted(low_obs_nodes),
        }

    def node_map(self) -> dict[str, Node]:
        return {n.node_id: n for n in self.nodes}

    def capability_map(self) -> dict[str, Capability]:
        return {c.capability_id: c for c in self.capabilities}

    def all_node_ids(self) -> set[str]:
        return {n.node_id for n in self.nodes} | {c.capability_id for c in self.capabilities}
