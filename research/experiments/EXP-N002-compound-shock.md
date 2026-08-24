# EXP-N002 — Compound shock behavior

- **experiment_id**: EXP-N002
- **question**: Does the compound incident (processor latency + region degradation + support outage) produce plausible, monotone, uncertainty-quantified behavior?
- **hypothesis**: Compound loss ≥ any component-subset loss; MC quantiles bracket the deterministic run; the floor breach is transient and lag-driven.
- **fixture_version**: digital_payments_v1
- **seed_policy**: seed 20260824; 100 MC replications sampling only declared fixture intervals
- **baseline**: single-component incidents
- **method**: invariant suite (component-removal monotonicity, no-improvement-without-action, redundancy monotonicity) plus 100-replication MC with seed-level storage.
- **metrics**: expected service loss, min service level, time-to-floor, floor-breach fraction, affected-node frequency
- **expected_failure_modes**: super-linear interaction the max-combination rule cannot express; breach fraction insensitive to declared intervals
- **result**: **pass** — deterministic run: min SL 67.5%, time-to-floor 25m, breach duration 160m; MC: floor breached in 63% of replications, max degradation p10–p90 = 0.262–0.355 (research/benchmark/compound_results.json)
- **error_analysis**: max-combination hides sub-dominant channels (fraud path) by construction; this is a declared assumption (asm_max_combination_v1), not a bug. The 63% breach fraction shows the breach is interval-sensitive — exactly the uncertainty the UI must show.
- **decision**: gate N-C holds for the fixture; keep max-combination for v0.1 and revisit with a saturating-sum variant as an explicit model v2.
- **next_step**: add a second aggregation rule as a fourth model to widen disagreement coverage.
