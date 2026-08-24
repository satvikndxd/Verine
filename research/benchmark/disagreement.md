# Disagreement benchmark (B7)

**Setup:** compound incident; deterministic propagation vs capacity-flow vs
Monte Carlo (median) vs reachability (set-only).

**Measured (seed 20260824):** overall level **material**. Largest areas:
- `recovery_time_minutes` — the steady-state model has no recovery dynamics;
  MC recovery spread is wide (declared recovery intervals).
- `affected_node_set` — reachability is a deliberate upper bound; capacity-flow
  under-reports weakly-coupled nodes (min-combination).
- `max_degradation` — max-combination (deterministic) vs min-channel (flow).

Every area carries likely reasons, missing evidence, and one recommended next
step; the evidence-request ranker consumes areas with normalized disagreement
≥ 0.15.

**Honesty note:** likely-reason strings come from a curated heuristic table in
`verine/evaluation/disagreement.py`, not from learned attribution.

**Status: pass** — disagreement is preserved, localized, and explained; never averaged away.
