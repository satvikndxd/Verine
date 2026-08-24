import pytest
from pydantic import ValidationError

from verine.capabilities.schema import Capability
from verine.common.ids import derived_id, validate_id
from verine.common.randomness import SeededRng
from verine.graph.edges import Edge
from verine.graph.nodes import Node
from verine.incidents.schema import Incident


def _cap(**kw):
    base = dict(
        capability_id="cap_test",
        name="Test",
        description="d",
        owner_role="ops",
        minimum_service_level=0.7,
        target_service_level=0.99,
        unit="tps",
        criticality="critical",
        valid_from="2026-01-01T00:00:00Z",
    )
    base.update(kw)
    return Capability(**base)


def test_capability_valid():
    assert _cap().capability_id == "cap_test"


def test_capability_min_above_target_rejected():
    with pytest.raises(ValidationError):
        _cap(minimum_service_level=0.999, target_service_level=0.9)


def test_unknown_enum_rejected():
    with pytest.raises(ValidationError):
        Node(node_id="node_x", node_type="blockchain", name="X")
    with pytest.raises(ValidationError):
        Node(node_id="node_x", node_type="vendor", name="X", epistemic_status="vibes")


def test_edge_lag_ordering_rejected():
    with pytest.raises(ValidationError):
        Edge(
            edge_id="edge_x",
            from_node="node_a",
            to_node="node_b",
            edge_type="requires",
            criticality_weight=0.5,
            propagation_lag_minutes={"min": 10, "median": 5, "max": 20},
        )


def test_compound_incident_needs_two_components():
    with pytest.raises(ValidationError):
        Incident(
            incident_id="inc_x",
            name="X",
            incident_type="compound",
            onset_at="2026-01-01T00:00:00Z",
            duration_minutes=60,
            severity=0.5,
            components=[
                {"target_node_id": "node_a", "mode": "latency", "severity": 0.5, "duration_minutes": 30}
            ],
        )


def test_component_window_must_fit_duration():
    with pytest.raises(ValidationError):
        Incident(
            incident_id="inc_x",
            name="X",
            incident_type="single",
            onset_at="2026-01-01T00:00:00Z",
            duration_minutes=60,
            severity=0.5,
            components=[
                {"target_node_id": "node_a", "mode": "latency", "severity": 0.5, "duration_minutes": 90}
            ],
        )


def test_id_validation():
    assert validate_id("cap_digital_payments", "capability")
    with pytest.raises(ValueError):
        validate_id("Capital-Letters", "capability")
    with pytest.raises(ValueError):
        validate_id("node_x", "capability")


def test_derived_id_stable():
    assert derived_id("case", {"a": 1}) == derived_id("case", {"a": 1})
    assert derived_id("case", {"a": 1}) != derived_id("case", {"a": 2})


def test_seeded_rng_reproducible_and_order_independent():
    a = SeededRng(42).substream("rep_3").uniform(0, 1)
    b = SeededRng(42).substream("rep_3").uniform(0, 1)
    assert a == b
    assert SeededRng(42).substream("rep_1").uniform(0, 1) != SeededRng(42).substream("rep_2").uniform(0, 1)
