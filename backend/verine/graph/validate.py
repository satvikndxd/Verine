"""Graph integrity validation.

Rejects dangling edges, duplicate ids, self-loops, dependency cycles
(dependency edges must form a DAG in v0.1), and invalid substitution refs.
"""

from __future__ import annotations

from ..common.errors import GraphInvalidError
from .snapshots import GraphSnapshot


def validate_graph(snapshot: GraphSnapshot) -> list[str]:
    """Return a list of warnings. Raise GraphInvalidError on hard failures."""
    errors: list[dict] = []
    warnings: list[str] = []

    all_ids = [n.node_id for n in snapshot.nodes] + [c.capability_id for c in snapshot.capabilities]
    seen: set[str] = set()
    for nid in all_ids:
        if nid in seen:
            errors.append({"field": "nodes", "reason": f"Duplicate node id {nid}"})
        seen.add(nid)

    edge_ids: set[str] = set()
    id_set = set(all_ids)
    for e in snapshot.edges:
        if e.edge_id in edge_ids:
            errors.append({"field": "edges", "reason": f"Duplicate edge id {e.edge_id}"})
        edge_ids.add(e.edge_id)
        if e.from_node == e.to_node:
            errors.append({"field": e.edge_id, "reason": "Self-loop edges are not allowed"})
        for endpoint in (e.from_node, e.to_node):
            if endpoint not in id_set:
                errors.append({"field": e.edge_id, "reason": f"Dangling endpoint {endpoint}"})
        for sub in e.substitution_options:
            if sub not in id_set:
                errors.append({"field": e.edge_id, "reason": f"Unknown substitution option {sub}"})

    # Dependency cycle check (Kahn) over dependency-direction edges.
    adj: dict[str, list[str]] = {nid: [] for nid in id_set}
    indeg: dict[str, int] = {nid: 0 for nid in id_set}
    for e in snapshot.edges:
        if e.from_node in id_set and e.to_node in id_set and e.from_node != e.to_node:
            adj[e.from_node].append(e.to_node)
            indeg[e.to_node] += 1
    queue = sorted([n for n, d in indeg.items() if d == 0])
    visited = 0
    while queue:
        n = queue.pop(0)
        visited += 1
        for m in sorted(adj[n]):
            indeg[m] -= 1
            if indeg[m] == 0:
                queue.append(m)
    if visited < len(id_set) and not errors:
        errors.append({"field": "edges", "reason": "Dependency graph contains a cycle; v0.1 requires a DAG"})

    for c in snapshot.capabilities:
        if not any(e.from_node == c.capability_id for e in snapshot.edges):
            warnings.append(f"Capability {c.capability_id} has no declared dependencies")

    for n in snapshot.nodes:
        if n.observability < 0.6:
            warnings.append(f"Node {n.node_id} has low observability ({n.observability}); blast radius may be underestimated")

    if errors:
        raise GraphInvalidError("Graph failed integrity validation", field_errors=errors)
    return warnings
