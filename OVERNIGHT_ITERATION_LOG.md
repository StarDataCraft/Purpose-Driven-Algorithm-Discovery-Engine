# Overnight iteration log

## Extended cycle 1 — OpenAlex request-storm prevention (2026-08-01)

- Problem: daily and transient HTTP 429 responses used a generic retry path and did not stop later OpenAlex queries.
- Root cause: OpenAlex shared the generic source adapter; there was no canonical session, rate state, run budget, limiter, or circuit.
- Repair: introduced one process-level client, typed `OpenAlexRateLimitState` and `QueryBudget`, API-key/anonymous modes, a global serialized limiter, daily/transient classification, bounded retry with `Retry-After`, circuit breaking, and redacted errors.
- Tests: daily exhaustion makes one HTTP call; transient 429 succeeds after the declared delay; repeated transient 429 opens the circuit; arXiv continues; API-key mode attaches a test credential internally without exposing it. Full suite: 116 passed.
- Actual output inspected: the daily-limit run records one concise category, skipped-query count, reset time, and retained arXiv output; no request URL or credential appears.
- Score before (workflow, practicality, readability, transparency, recovery, caution, specificity, visuals): 3, 2, 2, 2, 1, 3, 4, 5.
- Score after: 4, 4, 4, 5, 4, 5, 4, 5.
- Remaining issue: cache identity and external query fan-out still needed tightening.
- Next decision: coalesce duplicate requests and remove ML-slot contamination before scientific evaluation.

## Extended cycle 2 — native query budgeting and concise recovery (2026-08-01)

- Problem: external queries ended in ML slots such as `aggregation`, fanned out across five domains, and source failures were duplicated as sidebar JSON.
- Root cause: direction identity had been forced into retrieval text rather than preserved for typed alignment.
- Repair: limited Stage 1 to three domains and two native queries each, removed slot suffixes, normalized cache identity, coalesced duplicate requests, increased OpenAlex candidate retrieval to at least 25 per call, and replaced duplicate sidebar diagnostics with one primary status plus a technical expander.
- Tests: native-query validation, duplicate-query coalescing, anonymous budgets, and all prior workflow tests pass.
- Actual output inspected: Part 1/2 show a short anonymous-mode note or one rate-limit warning; query-level details remain technical.
- Score before: 4, 3, 3, 4, 3, 5, 4, 5.
- Score after: 5, 4, 5, 5, 4, 5, 4, 5.
- Remaining issue: benchmark the three scientific purposes and inspect two distinct direction paths.
- Next decision: run deterministic recurring-drift evaluation and inspect its full result.

Scores are clarity, practicality, readability, evidence transparency, error recovery, and visual hierarchy on a 0–5 scale.

## Cycle 1 — concrete candidate modification

- Classification: candidate synthesis presentation and result explanation.
- Observed problem: aggregation candidates displayed an empty “Change” because the UI read only `update_rule_delta`.
- Evidence: the recurring-drift result had `affected_component="aggregation"`, empty `update_rule_delta`, and `aggregation_delta="w[t+1] ∝ w[t] exp(-η loss[t])"`.
- Change: added one slot-aware modification selector and reused it in Part 2, Part 3, and the before/after diagram. Paper roles now distinguish direct evidence from context.
- Tests: 16 focused orchestration, AppTest, and diagram tests passed after the first repair.
- UI result: cards and the selected proposal show a non-empty rule for the actual modification slot.
- Rubric before: 4, 2, 3, 4, 4, 4.
- Rubric after: 4, 4, 4, 4, 4, 4.
- Remaining problem: proposal structure and mechanism mapping were still less explicit than the acceptance contract.

## Cycle 2 — one-minute explanation and complete mappings

- Classification: readability and diagram.
- Observed problem: proposal sections were implicit and the transfer diagram did not separately map signal, state, trigger, response, and failure risk.
- Change: added the required sections, exposed state/trigger/rule/inference inputs, expanded the evidence-to-idea chain to seven stages, expanded transfer to five typed mappings, and retained text fallbacks.
- Tests: deterministic fallback content and the explicit Part 3 structure are regression-tested.
- UI result: the proposal can be understood without opening technical JSON.
- Rubric before: 4, 4, 4, 4, 4, 4.
- Rubric after: 5, 5, 5, 5, 4, 5.
- Remaining problem: validate the full matrix, clean archive, live retrieval, local server, and deployed build.

## Model decision

No model was downloaded or adopted. The measured bottlenecks were deterministic presentation and field-selection defects; an encoder would not repair them and would add deployment cost.
