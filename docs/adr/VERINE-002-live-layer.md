# VERINE-002 — Live-intelligence layer over the synthetic kernel

Date: 2026-08-24
Status: Accepted

## Context

VERINE-001 established that the repo is the FastAPI + Next.js synthetic kernel
(no Tezcat/Vite). This ADR covers adding the real-time, evidence-bounded live
layer without disturbing the deterministic kernel.

## Decisions

1. **Separate service boundary.** The live plane lives in new subpackages
   (`vault`, `providers/{llm,live}`, `signals`, `hypotheses`, `analysis`,
   `streams`) and a `LiveService` orchestrator behind `/api/verine`. It calls
   the kernel's `VerineService` as a library; **live data never mutates kernel
   state**. External evidence is compiled into *declared scenario inputs*
   (incidents whose components are labeled `inferred`) that feed the existing
   deterministic analysis. The kernel's 51 tests remain green unchanged.

2. **Correlation window anchored on `retrieved_at`.** Signals co-observed within
   one operational window are candidate-correlated; each signal's `published_at`
   is preserved verbatim for replay eligibility. Rationale: a KEV published this
   morning and a status incident now are corroborating *observations* made
   together, even though their publication times differ by hours.

3. **`scenario_hash` excludes `created_at`/`scenario_id`.** A scenario's identity
   is its semantic inputs, so re-built forks with identical inputs replay
   byte-for-byte. This strengthened the kernel's determinism guarantee and left
   all replay tests green.

4. **Vault = AES-256-GCM + scrypt, fail-closed.** No `VERINE_VAULT_KEY` ⇒ no
   credential storage. Plaintext is never serialized: stored docs hold ciphertext
   only, API returns masked metadata only, decrypted keys live for one request
   and are registered with the redactor.

5. **Frontend adaptation (vs the prompt's `frontend/src/pages/*.jsx`).** The UI
   is Next.js App Router. New routes: `/live` (Live War Room), `/watch-packs`,
   `/providers`. The prior NERVE war room is retained as `/war-room` ("Sim Lab").
   Hash routes (`#/verine/...`) become path routes. The browser talks only to the
   Next.js server, which proxies `/api/*` to FastAPI — keys never transit the
   client.

6. **Offline-first.** `VERINE_LIVE_ENABLED=0` by default; connectors ship with
   offline fixtures and the same normalize path as live mode. The war room labels
   status honestly (`OFFLINE FIXTURES` / `LIVE` / `NO RECENT SIGNAL`).

## Consequences

- A clean checkout runs the full showcase with no network and no LLM.
- Enabling a live connector is a per-connector opt-in; nothing else changes.
- The moat data model (signals, evidence, hypotheses, shadow edges, cases) is
  captured with provenance from day one.
