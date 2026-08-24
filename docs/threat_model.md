# Threat model — v0.1

VERINE NERVE is a defensive resilience-analysis tool. It contains no exploit
generation, credential testing, intrusion, or automated change to real systems.

## Assets
Fixture/graph data (may later contain sanitized client topology), case files
(decision records), run integrity (hash lineage).

## Trust boundaries and mitigations
| Threat | Mitigation (v0.1) |
| --- | --- |
| Malicious/oversized JSON payloads | Pydantic strict contracts (`extra="forbid"`), enum validation, fixture size cap (5 MB), document size cap (20 MB), no arbitrary code in any payload |
| Prompt injection via imported text | No LLM in v0.1; all external documents are treated as untrusted DATA. If an LLM adapter is added, incident/evidence text must never be executed as instructions and must be fenced as data in any prompt |
| Runaway compute | Horizon cap (7 days), MC replication cap (500), step > 0 enforced, pathway depth cap |
| Tampered case files | sha256 lineage (graph/scenario/run); replay endpoint recomputes and compares; mismatch is surfaced, not repaired |
| Secrets leakage | No secrets in repo; no external network calls from the backend; synthetic data only by default |
| Cross-user data exposure | Single-tenant prototype; no auth by design (documented non-goal); do NOT deploy with real client data until authn/z exists |
| Immutability bypass | Snapshot store refuses to overwrite an id/hash with different content (409 CONFLICT) |

## Explicit rules for future integrations
Read-only access first; explicit user confirmation before any operational
action; every connector output enters the graph as evidence with provenance and
epistemic status, never as silent truth.
