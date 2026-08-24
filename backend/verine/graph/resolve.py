"""Entity and geography resolution against a watch pack's declared bindings.

Matching is transparent (exact or substring on lowercase aliases) and every
match records its reason. Fuzzy candidates are flagged review-required rather
than silently accepted."""

from __future__ import annotations

from ..signals.schema import ExternalSignal
from .watch_packs import WatchPack


def resolve_signal(signal: ExternalSignal, pack: WatchPack) -> dict:
    """Return {matches: [{node_id, matched_on, reason, review_required}], unmatched: [...]}"""
    matches: list[dict] = []
    unmatched: list[str] = []

    for entity in signal.entities:
        e = entity.lower().strip()
        hit = None
        for alias, node_id in pack.aliases.items():
            if e == alias:
                hit = {"node_id": node_id, "matched_on": entity, "reason": f"exact alias '{alias}'",
                       "review_required": False}
                break
            if alias in e or e in alias:
                hit = {"node_id": node_id, "matched_on": entity,
                       "reason": f"partial alias '{alias}' ~ '{e}'", "review_required": True}
        if hit:
            matches.append(hit)
        else:
            unmatched.append(entity)

    for geo in signal.geographies:
        g = geo.lower().strip()
        for binding in pack.geographies:
            if any(term in g for term in binding.match_terms):
                matches.append({
                    "node_id": binding.node_id,
                    "matched_on": geo,
                    "reason": f"geography '{binding.name}' term match",
                    "review_required": False,
                })
                break

    # Deduplicate by node, prefer non-review matches.
    by_node: dict[str, dict] = {}
    for m in matches:
        cur = by_node.get(m["node_id"])
        if cur is None or (cur["review_required"] and not m["review_required"]):
            by_node[m["node_id"]] = m
    return {"matches": sorted(by_node.values(), key=lambda m: m["node_id"]), "unmatched": unmatched}
