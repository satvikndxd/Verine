import pytest

from verine.capabilities.schema import Capability
from verine.common.errors import GraphInvalidError
from verine.graph.edges import Edge
from verine.graph.nodes import Node
from verine.graph.snapshots import GraphSnapshot
from verine.graph.validate import validate_graph


def _snapshot(edges, nodes=None):
    cap = Capability(
        capability_id="cap_t",
        name="T",
        description="d",
        owner_role="ops",
        minimum_service_level=0.5,
        target_service_level=0.9,
        unit="tps",
        criticality="high",
        valid_from="2026-01-01T00:00:00Z",
    )
    nodes = nodes or [
        Node(node_id="node_a", node_type="service", name="A"),
        Node(node_id="node_b", node_type="vendor", name="B"),
    ]
    return GraphSnapshot(graph_snapshot_id="graph_t", capabilities=[cap], nodes=nodes, edges=edges)


def _edge(eid, frm, to):
    return Edge(edge_id=eid, from_node=frm, to_node=to, edge_type="requires", criticality_weight=0.5)


def test_valid_graph_passes():
    warnings = validate_graph(_snapshot([_edge("edge_1", "cap_t", "node_a"), _edge("edge_2", "node_a", "node_b")]))
    assert isinstance(warnings, list)


def test_dangling_edge_rejected():
    with pytest.raises(GraphInvalidError) as exc:
        validate_graph(_snapshot([_edge("edge_1", "cap_t", "node_ghost")]))
    assert any("Dangling" in fe["reason"] for fe in exc.value.field_errors)


def test_cycle_rejected():
    with pytest.raises(GraphInvalidError) as exc:
        validate_graph(_snapshot([_edge("edge_1", "node_a", "node_b"), _edge("edge_2", "node_b", "node_a")]))
    assert any("cycle" in fe["reason"] for fe in exc.value.field_errors)


def test_duplicate_edge_id_rejected():
    with pytest.raises(GraphInvalidError):
        validate_graph(_snapshot([_edge("edge_1", "cap_t", "node_a"), _edge("edge_1", "cap_t", "node_b")]))


def test_graph_hash_stable_and_order_independent(bundle):
    h1 = bundle.snapshot.graph_hash()
    reversed_snapshot = GraphSnapshot(
        graph_snapshot_id=bundle.snapshot.graph_snapshot_id,
        capabilities=bundle.snapshot.capabilities,
        nodes=list(reversed(bundle.snapshot.nodes)),
        edges=list(reversed(bundle.snapshot.edges)),
    )
    assert reversed_snapshot.graph_hash() == h1
