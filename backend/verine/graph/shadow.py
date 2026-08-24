"""Shadowgraph: hypothesized shared dependencies, review-required by default.

Heuristic (transparent, documented): when one hypothesis maps ≥2 distinct
non-geography nodes and those nodes share a common declared dependency target
(including inferred edges) OR both signals carry overlapping geography, emit a
`possible_shared_dependency` shadow edge toward the common target. Shadow edges
are NEVER silently promoted — approval creates a new immutable snapshot."""

from __future__ import annotations

from ..common.ids import derived_id
from ..graph.snapshots import GraphSnapshot
from pydantic import BaseModel, ConfigDict, Field


class ShadowEdge(BaseModel):
    model_config = ConfigDict(extra="forbid")

    shadow_edge_id: str
    from_node_id: str
    to_node_id: str
    edge_type: str = "possible_shared_dependency"
    reason: str
    evidence_ids: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    epistemic_status: str = "inferred"
    requires_review: bool = True
    status: str = "proposed"  # proposed | approved | rejected
    hypothesis_id: str | None = None
    created_at: str = ""


def detect_shadow_edges(
    snapshot: GraphSnapshot,
    matched_node_ids: list[str],
    evidence_ids: list[str],
    hypothesis_id: str,
    created_at: str,
) -> list[ShadowEdge]:
    node_meta = snapshot.node_map()
    nodes = [n for n in matched_node_ids if n in node_meta and node_meta[n].node_type.value != "geography"]
    if len(nodes) < 2:
        return []

    # Outgoing dependency targets per node (declared, incl. inferred).
    targets: dict[str, set[str]] = {}
    for e in snapshot.edges:
        if e.from_node in nodes:
            targets.setdefault(e.from_node, set()).add(e.to_node)

    edges: list[ShadowEdge] = []
    seen_pairs: set[tuple[str, str]] = set()
    for i, a in enumerate(nodes):
        for b in nodes[i + 1:]:
            common = sorted(targets.get(a, set()) & targets.get(b, set()))
            if not common:
                continue
            target = common[0]
            for src in (a, b):
                # Only propose where no observed edge already exists.
                exists_observed = any(
                    e.from_node == src and e.to_node == target and e.epistemic_status.value == "observed"
                    for e in snapshot.edges
                )
                if exists_observed or (src, target) in seen_pairs:
                    continue
                seen_pairs.add((src, target))
                edges.append(
                    ShadowEdge(
                        shadow_edge_id=derived_id(
                            "shadow_edge", {"h": hypothesis_id, "f": src, "t": target}
                        ),
                        from_node_id=src,
                        to_node_id=target,
                        reason=f"Signals affecting {a} and {b} in one hypothesis; both declare a "
                               f"dependency path toward {target}. Records suggest shared infrastructure. "
                               "This is an inferred hypothesis, not a confirmed dependency.",
                        evidence_ids=evidence_ids,
                        confidence=0.5,
                        hypothesis_id=hypothesis_id,
                        created_at=created_at,
                    )
                )
    return edges
