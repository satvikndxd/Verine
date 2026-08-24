# Replay benchmark (B1/B9)

**Claim tested:** the same graph snapshot + incident + constraints + model set + seed reproduces identical run hashes across repeated executions and execution paths.

| Path | Result |
| --- | --- |
| In-process double execution | hash equal (tests/simulation/test_invariants.py) |
| API run → `/api/cases/{id}/replay` | hash equal (tests/api/test_api.py, e2e verify-replay) |
| CLI `fixture run` → `case replay` | hash equal (manual run, 2026-08-24) |

Representative hashes (seed 20260824, compound incident, horizon 720m):
- graph: `sha256:d356f95a0e6adaa658c69e7643bf981ee818e467539de03cd27d1518d1d291c1`
- run: `sha256:5c4b6c535b8bfdfddce959fa14113668c927ddef264da8253321437d01163286`

**Status: pass** on this platform. Cross-platform float reproducibility is untested (limitation).
