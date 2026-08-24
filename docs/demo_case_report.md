# Demo case report — compound payment crisis (synthetic)

**Everything below is a simulation over the synthetic digital_payments_v1
fixture (seed 20260824). Nothing describes a real organization.**

## Scenario
Digital Payments Authorization (target 99.5%, floor 70%) under a compound shock:
processor latency (sev 0.75, 180m), primary-region capacity loss (sev 0.70,
150m, +15m offset), vendor support outage (sev 0.80, 240m). Horizon 720m.

## What the compiler found
- **Blast radius:** 12 of 21 nodes affected (deterministic model).
- **Pathway:** capability ← identity provider ← primary region is the driving
  chain; gateway←region and database←region are close seconds.
- **Time-to-floor:** 25m; the breach is transient (160m) and lag-driven — no
  feasible action lands fast enough to prevent it entirely.
- **Containment:** cheapest feasible set = shift traffic to secondary region +
  escalate vendor hotline ($21k, both within deadline/roles/collateral):
  loss 1.22 → 0.80 sl·hours, breach 160m → 45m. 31 sets rejected with reasons
  (budget, missing treasury role, unmet backup-contract fact, collateral).
- **Uncertainty:** MC (100 reps over declared intervals) breaches the floor in
  63% of replications; max degradation p10–p90 = 0.26–0.36. Reliability: limited/weak
  once inferred shared-region edges are hidden.
- **Disagreement:** material — recovery-time estimates diverge most (steady-state
  vs time-dynamic vs sampled recovery). Generated evidence requests: run a
  failover drill; obtain backup activation SLA; confirm the inferred
  identity-provider/region and backup-processor/region dependencies.

## Limits of this report
Max-combination propagation hides sub-dominant channels by construction; action
effects are authored fixture parameters; the uncertainty heuristics are not
calibrated. Replay: `python -m verine.cli fixture run` reproduces the run hash.
