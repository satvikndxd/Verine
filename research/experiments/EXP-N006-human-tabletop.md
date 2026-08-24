# EXP-N006 — Human tabletop protocol (NOT YET RUN)

- **experiment_id**: EXP-N006
- **question**: Do users identify the main bottleneck faster, and propose better-constrained containment plans, with the war room versus a static dependency list?
- **hypothesis**: Time-to-bottleneck and plan feasibility improve; overconfidence does NOT increase (calibration question included).
- **fixture_version**: digital_payments_v1
- **seed_policy**: fixed seed per session; both conditions see identical scenario data
- **baseline**: static dependency list + incident description (spreadsheet condition)
- **method** (blinded, within-subjects, order counterbalanced):
  1. Recruit ≥4 participants with ops/risk background; none may have seen the fixture.
  2. Condition A: spreadsheet of nodes/edges + incident text. Condition B: war room UI.
  3. Tasks per condition: (a) name the dependency chain driving capability loss; (b) propose a containment plan within budget/deadline; (c) state confidence 0-100%; (d) list dependencies you suspect are missing.
  4. Score against fixture ground truth; log times; rate plan feasibility with the constraint checker.
- **metrics**: time-to-bottleneck, pathway correctness, plan feasibility rate, expected-loss of proposed plan (simulated), confidence calibration, missing-dependency discovery count, perceived usefulness (1-7)
- **expected_failure_modes**: UI slower due to learning curve; graph seduces users into wrong-but-visible paths; calibration worsens
- **result**: **pending — this experiment has not been run. No human data exists. Results will be logged to research/benchmark/human_results.csv verbatim.**
- **error_analysis**: n/a
- **decision**: n/a (gates N-F and N-G blocked until this runs)
- **next_step**: schedule two pilot sessions; freeze the fixture version beforehand.
