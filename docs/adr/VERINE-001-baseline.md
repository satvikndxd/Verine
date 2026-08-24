# VERINE-001 — Baseline before the live-intelligence build

Date: 2026-08-24
Status: Accepted

## What exists (commit `19cf563`)

The repository contains the **VERINE NERVE v0.1** synthetic prototype built in the
previous phase. There is **no Tezcat code, no React/Vite frontend, and no
prediction-market surface** anywhere in the tree — the master prompt's
assumptions about a historical implementation do not apply; the actual stack is:

| Layer | Actual implementation |
| --- | --- |
| Backend | Python 3.11, FastAPI, Pydantic v2, package `backend/verine` |
| Frontend | **Next.js 15 App Router** (`apps/web`), Tailwind v4, React Flow |
| Storage | File-backed `FileStore`/`Repositories` (ADR-001), Postgres DDL authored |
| Simulation | Deterministic discrete-time engine + reachability/capacity-flow/Monte Carlo |
| Artifacts | Canonical-JSON sha256 hashing, immutable snapshots, CaseFile + replay |
| Tests | 51 pytest (unit/simulation/replay/api) + 3 Playwright e2e — **all green at baseline** |

## Reusable kernel (preserve, do not rebuild)

- `verine.common.hashing` (canonical JSON + sha256), `verine.common.randomness`
  (seeded, order-independent substreams), epistemic enums
- Graph contracts + immutable snapshots + integrity validation
- Scenario compiler, propagation engine, model ensemble, disagreement report,
  unknowns detector, containment optimizer, evidence-request ranker
- CaseFile runner + byte-for-byte replay; file-backed repositories
- Existing `/api/*` endpoint contract and the war-room UI (kept as the
  scenario/simulation lab surface)

## Adaptations of the master prompt to this repository

1. Frontend artifacts specified as `frontend/src/pages/*.jsx` are implemented as
   Next.js routes/components under `apps/web/app` and `apps/web/components`.
2. Routes specified as `#/verine/...` hash routes become path routes
   (`/live`, `/watch-packs`, `/providers`, `/cases`, `/evidence`, `/settings`).
3. The new live layer lives in new subpackages of `backend/verine`
   (`vault`, `providers`, `signals`, `hypotheses`, `analysis`, `streams`) behind
   a separate `/api/verine` namespace; the synthetic kernel is **never mutated
   by live data** — live evidence compiles into *declared scenario inputs*
   (incident hypotheses with `inferred`/`model_result` status) that feed the
   existing deterministic analysis layer.
4. Existing routes and tests remain untouched and must stay green (regression
   gate for every phase).

## Baseline verification

- `pytest tests/unit tests/simulation tests/replay tests/api -q` → 51 passed
- `npx playwright test` → 3 passed (war-room happy path, hidden topology, a11y)

Deviations, if any arise during the build, are recorded in subsequent ADRs.
