# ADR-001: Repository strategy for VERINE NERVE v0.1

Date: 2026-08-24
Status: Accepted

## Context

Phase 0 reconnaissance (commit `5df3c94`) found the repository empty except for a
one-line `README.md` ("# Verine"). There is no existing application, no tests, no
package manifests, and no deployment configuration. Baseline test run: **no test
suite exists** (`pytest` not installed at baseline; nothing to run). Nothing can be
overwritten because nothing exists.

Environment constraints observed in the build sandbox:

| Facility | Available? |
| --- | --- |
| Python 3.11.2 | yes |
| Node 22 / npm | yes |
| pip | bootstrapped into a venv via get-pip (no system pip) |
| Docker / docker-compose | **no** |
| PostgreSQL server | **no** |
| Outbound network (npm/pypi) | yes |

## Decision

1. **Greenfield build** following the VERINE NERVE build brief: modular Python
   monolith under `backend/verine/`, FastAPI entrypoint under `apps/api/`,
   Next.js web app under `apps/web/`, fixtures/tests/docs/research per the brief.
2. **Persistence:** the brief specifies PostgreSQL. This sandbox has no Postgres
   server and no Docker. To keep v0.1 runnable from a clean checkout, persistence
   is implemented behind a typed repository interface
   (`backend/verine/api/repositories.py`) with a **file-backed JSON store**
   (`data/` directory, canonical JSON documents, hash-checked). The initial
   PostgreSQL migration (`db/migrations/001_initial.sql`) is authored and kept in
   sync with the contracts so a Postgres-backed repository can be swapped in
   without changing routers or domain code. This is a deliberate, documented
   deviation, not a hidden one.
3. **Graph visualization:** React Flow (`@xyflow/react`) rather than Cytoscape.js.
   Reasons: first-class React integration with the Next.js App Router, typed
   nodes/edges, easy per-edge styling for epistemic status (observed / inferred /
   simulated / unknown), and smaller conceptual surface for a v0.1 that renders
   ~25 nodes. Recorded here per the brief's requirement to choose one and
   document the decision.
4. **No LLM adapter in v0.1.** The demo must work without one; an adapter
   interface can be added later behind `backend/verine/models/`.
5. **Determinism policy:** all randomness flows through
   `verine.common.randomness.SeededRng`; no wall-clock reads inside simulation
   code; canonical JSON + SHA-256 hashing for graph/scenario/run/case artifacts.

## Consequences

- A clean checkout runs with `python -m venv`, `pip install -e backend`, and
  `npm install` in `apps/web` — no external services required.
- Postgres adoption later is a repository-implementation swap plus running the
  already-authored migration.
- All simulated outputs are labeled `simulated`/`model_result`; nothing in v0.1
  claims real-world predictive accuracy.
