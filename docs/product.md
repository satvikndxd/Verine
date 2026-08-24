# VERINE NERVE — Product

## What it is
A **capability-level crisis compiler**. Input: a critical business capability, its
dependency graph, a (possibly compound) incident, and response constraints.
Output: a versioned, replayable **Resilience Case File** containing the blast
radius, time-to-impact pathway, uncertainty map, competing model views, the
smallest feasible containment set, and the next evidence to gather.

Category: **Capability-Level Resilience Intelligence**. It is not a SIEM, SOAR,
vendor score, CMDB, BC document store, digital twin, LLM analyst, or autonomous
incident commander.

## v0.1 honesty rules (enforced in code and UI)
1. Observed / inferred / simulated / hypothesized data carry distinct labels
   (epistemic enum, edge/node styling, badges).
2. Simulated results are never shown as predictions of real companies (global
   SYNTHETIC MODE banner + per-panel labels + case-file disclaimer).
3. Inferred dependencies render dashed amber and are never called confirmed.
4. Every impact event links its rule and assumption ids.
5. Impact estimates carry time ranges and an uncertainty object (aleatoric,
   epistemic, observability, model disagreement, interval).
6. Actions expose cost, duration, roles, reversibility, collateral, side effects.
7. Incomplete topology raises reported uncertainty (unknowns panel) instead of
   silently shrinking the blast radius.
8. Model disagreement is preserved and explained, never averaged away.
9. Case files export the graph/scenario/run hashes, seed, model versions, and
   replay verbatim.
10. No generated sentence appears without its evidence or simulation basis.

## Demo story (v0.1, working end-to-end)
Digital Payments Authorization under a compound shock (processor latency +
primary-region degradation + vendor support outage): the floor is breached
transiently at t≈25m through the identity-provider/region pathway; the cheapest
feasible containment ($21k: shift traffic to the secondary region + escalate the
vendor hotline) cuts the breach from 160m to 45m and loss by ~34%; models
disagree materially on recovery time, which generates ranked evidence requests
(failover drill, backup SLA). Every number above is a simulation over the
synthetic fixture.

## Who it is for first
Regulated or operationally complex organizations and their advisors, sold first
as a manual analysis + workshop (one capability, one case file, one walkthrough),
NOT as software. See research/customer/ for the interview guide and pilot contract.

## What is deliberately not built (v0.1)
Live feeds, autonomous response, production integrations, exploit tooling,
a general CMDB, vector DB, graph DB, RL, multi-tenant billing, a single
"resilience score", or claims of real-world predictive accuracy.
