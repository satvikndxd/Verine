# VERINE NERVE

**A capability-level crisis compiler for enterprise resilience — synthetic,
evidence-bounded prototype (v0.1).**

VERINE NERVE converts a critical business capability, its dependency graph, and
a multi-domain (compound) incident into an auditable blast-radius analysis, a
time-to-impact pathway, the smallest feasible containment set, and the next
evidence required to reduce uncertainty — exported as a replayable
**Resilience Case File**.

> ⚠️ **Synthetic results only.** This prototype simulates authored fixture
> graphs. Its outputs are model results — labeled observed / inferred /
> simulated / unknown throughout — and are **never forecasts about real
> organizations, real outages, or real recovery**. No live integrations exist
> or are needed for the demo.

## Quick start (no database, no Docker required)
```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -e backend[dev]
cd apps/web && npm install && cd ../..

# terminal 1 — API
cd apps/api && uvicorn main:app --port 8000

# terminal 2 — UI
cd apps/web && npm run dev
```
Open http://localhost:3000, open the war room, inject the
**compound payment crisis**, scrub the timeline, tighten the containment
budget, inspect model disagreement and unknowns, export the case file, and
verify its replay hash.

CLI equivalent: `python -m verine.cli fixture run`.

## What works end-to-end
- Deterministic discrete-time propagation with documented rules and seeded RNG
- Four models (reachability, deterministic, capacity-flow, Monte Carlo) that
  are compared, never averaged — disagreement is localized and explained
- Containment optimizer with transparent weights, constraint rejection reasons,
  runner-up sets, and evidence requests when nothing robust exists
- Incomplete-topology mode: hidden dependencies raise reported uncertainty
- Case files with graph/scenario/run hash lineage and byte-for-byte replay
- 51 backend tests + 3 Playwright browser tests; benchmarks B1–B7, B9 pass
  (B8/B10 honestly `pending` until humans run the tabletop)

## Repository map
`backend/verine` (domain + engine + API) · `apps/web` (Next.js war room) ·
`apps/api` (FastAPI entrypoint) · `fixtures/` (synthetic payments graph +
evidence) · `tests/` · `db/migrations/` (Postgres DDL, see ADR-001) · `docs/`
(product, architecture, model card, threat model, runbook) · `research/`
(experiments, benchmarks, customer research, ADRs).

## Honesty rules
See `docs/product.md`. The short version: epistemic status is first-class,
simulated ≠ observed, inferred ≠ confirmed, disagreement is a signal, and every
number can be traced to a rule, assumption, evidence record, or seed.
