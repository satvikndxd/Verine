# Manual pilot case (N076) — TEMPLATE, NOT YET DELIVERED

Status: **pending**. No real-user pilot has been delivered. This template is the
delivery contract for the first one.

## Scope
- Input: one critical capability, one sanitized dependency list (client-provided,
  anonymized node names allowed), one compound incident chosen with the client.
- Output: one Resilience Case File (JSON + Markdown), one 60-minute live
  walkthrough in the war room, one revision within a week.

## Protocol
1. Intake call: capture capability, service-level definition, dependency list,
   candidate actions with rough costs/durations. Everything is entered as a new
   fixture with epistemic_status = observed only where the client attests it.
2. Author incident scenarios with the client (their last real incident, replayed,
   is preferred over an invented one).
3. Run, review internally, deliver walkthrough. Record which dependency the
   client did not know about, and whether any decision changed.

## Measures (to be filled during/after delivery)
- time_saved_estimate: __
- missing_dependency_found (y/n + which): __
- decision_changed (y/n + which): __
- trust_rating_1_7: __
- willingness_to_pay_quote: __
- second_analysis_requested (gate N-G) (y/n): __
