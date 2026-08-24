# Runbook

## Prerequisites
Python 3.11+, Node 20+. No database or Docker required for the demo (ADR-001).

## Setup (clean checkout)
```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -e backend[dev]          # or: pip install -e backend && pip install pytest
cd apps/web && npm install && cd ../..
```

## Run
```bash
# API (port 8000) — seeds the fixture into ./data on startup
cd apps/api && VERINE_DATA_DIR=$PWD/../../data uvicorn main:app --port 8000 &

# Web (port 3000) — proxies /api/* to the API
cd apps/web && npm run dev           # or: npm run build && npm run start
```
Open http://localhost:3000 → "Open war room" → pick the compound incident → Inject.

## CLI
```bash
python -m verine.cli fixture run                          # run compound demo, print hashes
python -m verine.cli --data-dir /tmp/v fixture run        # persist store for replay
python -m verine.cli --data-dir /tmp/v case replay case_… # byte-for-byte replay check
python -m verine.cli benchmark                            # B1–B10 report
```

## Tests
```bash
python -m pytest tests/unit tests/simulation tests/replay tests/api -q   # 51 tests
cd apps/web && npx playwright install chromium                            # once
npx playwright test                                                       # e2e (servers must be running)
```
The e2e specs live in tests/e2e/ and resolve @playwright/test through the
tests/e2e/node_modules symlink (relative, committed via make e2e-link if missing).

## Troubleshooting
- 409 CONFLICT on snapshot POST: snapshots are immutable by design; change the id.
- Empty UI lists: the API seeds fixtures on startup; check /api/health then /api/presets.
- Replay mismatch: the store's scenario/graph changed after the case was written —
  that is the tamper-evidence feature working, not a bug.
