# VERINE live-layer status (EXP-V001…V014)

All engineering experiments run offline against fixtures; nothing here claims
real-world predictive validity. Human/customer experiments stay **pending**.

| ID | Experiment | Status | Evidence |
| --- | --- | --- | --- |
| EXP-V001 | Connector normalization (6 types) | pass | tests/verine/test_connectors.py |
| EXP-V002 | Raw artifact + cursor replay / dedup | pass | test_live_pipeline::test_dedup_on_repoll, RawArchive hashing |
| EXP-V003 | Evidence quorum (independent groups) | pass | test_three_signals_corroborate_into_one_hypothesis |
| EXP-V004 | Hidden-dependency shadowgraph | pass | test_shadow_edge_review_required (backup_processor→cloud_region) |
| EXP-V005 | Cascade-clock intervals + assumptions | pass | test_cascade_clock_intervals_and_assumptions |
| EXP-V006 | Model disagreement localization | pass | kernel disagreement report reused in case file |
| EXP-V007 | Containment feasibility | pass | test_fork_is_immutable_and_replayable |
| EXP-V008 | Containment robustness | partial | robustness evaluator exists; fork robustness UI pending |
| EXP-V009 | LLM citation + schema validation | pass | test_citation_enforcement_flags_unknown_evidence |
| EXP-V010 | LLM cost / budget limits | pass | test_budget_limit_blocks_requests |
| EXP-V011 | End-to-end live fixture stream | pass | tests/e2e/verine-live.spec.ts |
| EXP-V012 | Deterministic case replay | pass | kernel replay + fork run-hash equality |
| EXP-V013 | Human tabletop comparison | **pending** | requires participants (see EXP-N006 protocol) |
| EXP-V014 | Manual customer pilot | **pending** | requires a real analyst |

## Honesty notes

- The cascade clock's severity/duration are **declared inferred inputs**, not
  measurements. Shadow-edge confidence is a fixed heuristic, not calibrated.
- External signals never auto-promote to confirmed internal impact; the only path
  to `USER_CONFIRMED_IMPACT` is an explicit human actor + reason (audited).
- Live mode against real providers is **untested here** (offline sandbox). The
  connectors are built to the documented public APIs but have not been exercised
  against live endpoints; that is Phase 6 and must be recorded honestly when run.
