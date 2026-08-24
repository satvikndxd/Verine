# EXP-N003 — Containment optimization

- **experiment_id**: EXP-N003
- **question**: Does exhaustive/greedy containment search find feasible sets that beat no-action, and reject infeasible sets with reasons?
- **hypothesis**: On the compound case a small feasible set materially reduces loss; role/budget/collateral/fact constraints prune the space.
- **fixture_version**: digital_payments_v1
- **seed_policy**: seed 20260824
- **baseline**: greedy action ranking; no-action baseline
- **method**: exhaustive enumeration of action subsets (size ≤ 3) under default constraints; utility with user-visible weights; per-set re-simulation.
- **metrics**: loss reduction, floor-breach duration reduction, rejection reasons coverage, feasibility of all ranked sets
- **expected_failure_modes**: mis-scaled utility weights letting cheap useless actions win; infeasible set leaking into ranking
- **result**: **pass** — chosen set {traffic shift to secondary region + vendor hotline}, $21k: loss 1.22 → 0.80 sl·hours, floor breach 160m → 45m; 31 sets rejected with explicit reasons. NOTE: an earlier weight configuration DID let a near-useless cheap action win — caught and fixed during development; weights are now surfaced in every response.
- **error_analysis**: no feasible set prevents the transient breach at t≈25m (action lead times exceed lag-driven onset). This is reported honestly as `transient_floor_breach_containment_partial`, and motivates the pre-staged-failover evidence request.
- **decision**: gate N-D holds; keep transparent-weight utility, never hard-code an optimum.
- **next_step**: robustness screening of the chosen set across declared severity multipliers in the UI.
