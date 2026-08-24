# Model card — VERINE NERVE v0.1 simulation models

## Scope and intent
All models operate on SYNTHETIC fixture graphs. Outputs are labeled
`model_result`/`simulated` and are decision-analysis aids for tabletop
exercises. **None of these models predicts real outages, cyberattacks,
corporate failure, or real-world recovery.** No evaluation against real-world
incidents exists.

## Models
### reachability_v1
Reverse reachability from incident targets over dependency edges. Deliberate
upper bound; ignores weights, lags, capacity, redundancy.

### deterministic_propagation_v1
Discrete-time (5-minute steps). Rules (all declared assumptions):
- direct effect = severity × mode multiplier while active; linear recovery after
- edge impact = weight × delayed source degradation × capacity fraction × (1 − redundancy)
- redundancy = best substitute's substitutability × its health (previous step)
- channels combine by MAX (asm_max_combination_v1) — monotone by construction
- actions multiply target degradation by (1 − capacity_effect) once effective
Known limits: cannot express super-linear compound interactions; median lag only;
effective minimum lag is one step.

### capacity_flow_v1
Steady-state bottleneck approximation at peak stress (min-channel availability,
redundancy adds capacity). A business is NOT literally a static flow network;
the model exists to disagree informatively with the time-dynamic model. No lags,
no recovery dynamics.

### monte_carlo_v1
100 seeded replications of the deterministic engine, sampling ONLY declared
fixture intervals (component severity/duration, edge lag, node recovery).
Triangular sampling. Reports quantiles and seed-level results; never a bare mean.
Uncertainty NOT captured: structural (missing edges), parametric outside declared
intervals, model-form error.

## Disagreement and unknowns
Disagreement areas carry curated (not learned) reason hints. The unknowns
detector's uncertainty increase for hidden/inferred edges is a designed heuristic,
not a calibrated probability.

## Optimizer
Exhaustive (≤3 actions) or greedy; transparent utility with user-visible weights;
constraint checking before ranking. Effects are fixture parameters — rankings are
NOT causal effect estimates.

## Evaluation status
Engineering benchmarks B1–B7, B9: pass (research/benchmark/). Human benchmarks
B8, B10: **pending** — no human data exists. Cross-platform hash reproducibility:
untested.
