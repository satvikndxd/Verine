"""Evidence quorum: count INDEPENDENT source groups, apply transition rules.

one weak source                  -> UNCONFIRMED
one strong source                -> OBSERVED_EXTERNAL_SIGNAL
independent corroboration        -> CORROBORATED
mapped capability impact         -> OPERATIONALLY_RELEVANT_HYPOTHESIS
contradictory evidence           -> CONTESTED
"""

from __future__ import annotations


def compute_quorum(
    signal_groups: list[dict],  # [{independence_group, strength}]
    has_capability_mapping: bool,
    has_contradiction: bool,
) -> dict:
    groups = sorted({g["independence_group"] for g in signal_groups if g["independence_group"]})
    strong = [g for g in signal_groups if g.get("strength") == "strong"]

    if has_contradiction:
        target = "CONTESTED"
    elif len(groups) >= 2 and has_capability_mapping:
        target = "OPERATIONALLY_RELEVANT_HYPOTHESIS"
    elif len(groups) >= 2:
        target = "CORROBORATED"
    elif strong and has_capability_mapping:
        target = "OPERATIONALLY_RELEVANT_HYPOTHESIS"
    elif strong:
        target = "OBSERVED_EXTERNAL_SIGNAL"
    else:
        target = "UNCONFIRMED"

    return {
        "independent_groups": groups,
        "independent_group_count": len(groups),
        "strong_signal_count": len(strong),
        "has_capability_mapping": has_capability_mapping,
        "has_contradiction": has_contradiction,
        "target_state": target,
        "rule": "≥2 independent groups → corroborated; capability mapping upgrades to "
                "operationally-relevant; contradictions force contested",
    }
