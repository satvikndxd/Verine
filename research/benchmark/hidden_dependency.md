# Hidden-dependency benchmark (B6)

**Setup:** compound incident run twice — full topology vs. `hidden_edge_ids = [edge_idp_region, edge_backup_region]` (the two INFERRED shared-region edges).

**Measured (seed 20260824):**
- epistemic uncertainty: rises when edges are hidden (see engineering_benchmark_v0_1.json task B6 for the exact values of this run)
- unknowns panel emits `undisclosed_dependencies` with the hidden count
- reliability label degrades; hidden edges never silently disappear

**Interpretation honesty:** the uncertainty increase is a declared heuristic
(hidden-fraction weighting in `verine/evaluation/unknowns.py`), not a calibrated
probability. The demo point stands: two "independent" payment processors sharing
an inferred cloud-region dependency is exactly the blind spot the incomplete-topology
mode is designed to surface.

**Status: pass** (engineering criterion); calibration is future work.
