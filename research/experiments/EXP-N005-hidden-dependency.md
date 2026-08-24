# EXP-N005 — Hidden dependency handling

- **experiment_id**: EXP-N005
- **question**: When declared dependencies are hidden from the models (incomplete-topology mode), does reported uncertainty rise and does the unknowns panel disclose the gap?
- **hypothesis**: Hiding the two inferred shared-region edges (identity provider and backup processor) increases epistemic uncertainty and surfaces an `undisclosed_dependencies` unknown.
- **fixture_version**: digital_payments_v1 (hidden: edge_idp_region, edge_backup_region)
- **seed_policy**: seed 20260824
- **baseline**: complete graph
- **method**: run the compound scenario with and without hidden edges; compare uncertainty components and the unknowns list; e2e assertion in tests/e2e/war-room.spec.ts.
- **metrics**: epistemic uncertainty delta, unknown kinds emitted, blast-radius delta
- **expected_failure_modes**: hidden edges silently vanishing (uncertainty unchanged) — an honesty-rule violation
- **result**: **pass** — epistemic uncertainty rises (benchmark B6); unknowns panel reports the count of undisclosed dependencies without leaking which they are; the two "independent" processors sharing a region is exactly the failure this scenario demonstrates
- **error_analysis**: the uncertainty increase is a designed heuristic (hidden-fraction weighting), not a calibrated probability — labeled as such.
- **decision**: honesty rule 7 holds in the pipeline and UI.
- **next_step**: calibrate the uncertainty heuristic against synthetic ground truth over many random hidden-edge draws.
