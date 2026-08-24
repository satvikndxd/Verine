# EXP-N004 — Model disagreement interpretability

- **experiment_id**: EXP-N004
- **question**: When the deterministic, capacity-flow, and Monte Carlo models disagree, is the disagreement localized and explained rather than averaged away?
- **hypothesis**: The steady-state capacity-flow model overstates degradation (no lags, min-combination) versus the time-dynamic model; recovery estimates diverge most.
- **fixture_version**: digital_payments_v1
- **seed_policy**: seed 20260824
- **baseline**: ensemble average (rejected by design)
- **method**: normalized pairwise differences on max degradation, time-to-floor, recovery, affected-set Jaccard; each area carries likely reasons, missing evidence, and a recommended next step.
- **metrics**: normalized disagreement per metric, overall level
- **expected_failure_modes**: disagreement reported without causes; models accidentally identical (report vacuous)
- **result**: **pass** — compound case yields level "material"; largest gaps on recovery time and affected-set composition; every area carries reasons and a next step (benchmark B7)
- **error_analysis**: reason hints are a curated heuristic table, not learned attributions — documented as such in the model card.
- **decision**: gate N-E holds.
- **next_step**: track whether evidence requests generated from disagreement actually reduce it when fulfilled (requires pilot data).
