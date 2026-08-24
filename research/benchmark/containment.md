# Containment benchmark (B5)

**Setup:** compound incident, default constraints (budget $100k, deadline 120m,
roles {payments_operations, engineering_on_call}, max collateral 0.30,
facts {backup_contract_active}), exhaustive search over action subsets ≤ 3.

**Measured (seed 20260824):**

| Set | Loss (sl·h) | Floor breach | Cost |
| --- | --- | --- | --- |
| No action | 1.223 | 160m (starts t=25m) | $0 |
| **Chosen: traffic shift + vendor hotline** | **0.803** | **45m** | **$21k** |
| Runner-ups | 0.80–0.84 | 45m | $23k–$28k |

- 31 candidate sets rejected, each with explicit reasons (budget, roles,
  unmet feasibility facts, collateral, duplicate targets).
- All ranked sets re-verified feasible by the constraint checker (test-enforced).
- No feasible set prevents the transient breach — action lead times exceed the
  lag-driven onset. Reported as `transient_floor_breach_containment_partial`,
  never hidden.

**Status: pass.** Caveat: all effects are simulated fixture parameters; the
optimizer output is a decision-analysis ranking, not a causal effect estimate.
