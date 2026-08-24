# Customer interview guide (v0.1)

Target personas: CISO / third-party-risk lead, COO / operational-resilience lead,
technology-risk lead, turnaround consultant, board risk-committee support.

Rule: ask about actual past behavior, never "would you use this?" Do not demo
before section 4.

## 1. Last incident (20 min)
- Walk me through the last time a vendor or infrastructure problem degraded a
  business service. What broke first? How did you find out?
- What did you have to produce, for whom, and by when (board memo, regulator
  notice, exec update)? Can I see a redacted example?
- What did you know at hour 1 vs hour 4? What did you wish you knew?
- Which dependency surprised you? Who knew about it beforehand?

## 2. Last risk review / continuity test (15 min)
- When was your last continuity or failover test for a revenue-critical service?
  What did it cost to run? What did it change?
- How is your dependency inventory maintained today? Who trusts it? Why/why not?
- Show me the artifact your last third-party risk review produced. Who read it?

## 3. Decision and spend evidence (10 min)
- What did the last incident cost (estimate is fine)? What was approved
  afterwards (budget, headcount, tooling)?
- Who can approve a $25-75k analysis engagement? What did that person last
  approve in this space?

## 4. Concept probe (10 min — only now show the case file)
- Here is a Resilience Case File for a synthetic payment capability. What in
  this would have changed a decision in your last incident? What is missing?
- If we produced this for one of YOUR capabilities from a sanitized dependency
  list, what would you pay for the first one? Who else would need to see it?

## Log per interview
persona, org type, last-incident summary, artifact demanded, budget evidence,
strongest objection, exact quotes, willingness-to-pay signal, follow-up agreed (y/n).
