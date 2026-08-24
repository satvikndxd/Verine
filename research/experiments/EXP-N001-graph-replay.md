# EXP-N001 — Graph and case-file replay determinism

- **experiment_id**: EXP-N001
- **question**: Does `graph_snapshot + incident + constraints + model_version + seed` always yield an identical canonical result and run hash?
- **hypothesis**: With canonical JSON, a seeded RNG, and no wall-clock reads, replay is byte-for-byte identical.
- **fixture_version**: digital_payments_v1
- **seed_policy**: fixed seed 20260824; MC substreams derived as sha256(seed, label)
- **baseline**: hash and schema checks (re-run comparison)
- **method**: run the compound scenario twice in-process (tests/simulation/test_invariants.py::test_replay_hash_identical), and through the API replay endpoint (tests/replay, tests/api); CLI `verine case replay`.
- **metrics**: run-hash equality, metrics equality, scenario/graph hash lineage
- **expected_failure_modes**: dict-ordering nondeterminism, float non-associativity across platforms, hidden randomness, wall-clock leakage into hashed payloads
- **result**: **pass** — hashes identical across in-process, API, and CLI replays (benchmark B1, B9)
- **error_analysis**: none observed; float behavior is deterministic on a single platform. Cross-platform (x86 vs ARM) reproducibility is UNTESTED — flagged as a limitation in docs/model_card.md.
- **decision**: determinism gate N-A holds; safe to build persistence and UI on run hashes.
- **next_step**: add a cross-platform replay check in CI when a second architecture is available.
