# Architecture

Modular monolith. See ADR-001 for the repository strategy and deviations.

```
apps/web        Next.js 15 App Router UI (React Flow graph, SVG timeline)
apps/api        FastAPI entrypoint (thin; imports verine.api.app)
backend/verine  Python 3.11 domain package
  common/         canonical JSON + sha256, seeded RNG, ids, enums, errors, uncertainty
  capabilities/   Capability contract
  graph/          Node/Edge contracts, immutable snapshots, integrity validation
  incidents/      Incident + compound components (declared sampling intervals)
  simulation/     Scenario contract, compiler, discrete-time propagation engine
  models/         reachability, deterministic, capacity-flow, Monte Carlo
  optimization/   actions, constraints, exhaustive + greedy search, robustness
  evidence/       evidence/assumption records, information-request ranker
  cases/          CaseFile contract, runner, replay
  evaluation/     metrics, comparison, disagreement, unknowns, benchmarks
  api/            repositories (file store), service layer, routers, errors
db/migrations   PostgreSQL DDL kept in sync with contracts (not active in sandbox)
fixtures/       digital_payments_capability.json + evidence.json + expected/
tests/          unit / simulation / replay / api / e2e (Playwright)
research/       experiments, benchmarks, customer research, ADRs
```

## Determinism contract
- All randomness flows through `SeededRng` (sha256-derived substreams, order-independent).
- No wall-clock reads inside simulation code; `executed_at` is applied at the API
  boundary and excluded from run hashes.
- Canonical JSON (sorted keys, compact, NaN-rejected) for every hashed artifact.
- `run_hash = sha256(graph_hash + scenario_hash + seed + model outputs)`.

## Data flow
capability + snapshot + incident + constraints → scenario compiler (fail-fast
validation) → model set (each independent) → comparison + disagreement →
unknowns/uncertainty → containment optimizer → evidence requests → CaseFile →
store → replay endpoint re-executes and compares hashes.

## Key decisions
- **File-backed store** behind a typed repository interface (no Postgres/Docker
  in the sandbox); migration SQL is authored so the swap is mechanical.
- **React Flow** over Cytoscape (ADR-001) with a deterministic layered BFS layout.
- **Max-combination** propagation (worst channel dominates) chosen for provable
  monotonicity; documented as assumption asm_max_combination_v1.
- **No LLM anywhere** in v0.1; the pipeline is fully deterministic.
