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

## Extended cycle 3 — honest gap-funnel accounting (2026-08-01)

- Problem: recurring drift reported 34 “valid gaps” from four evidence-bearing papers, obscuring the bounded production portfolio.
- Root cause: the benchmark funnel counted every non-error detector instance as a valid gap instead of reporting evidence events, raw instances, canonical families, and promoted directions separately.
- Repair: expanded the typed funnel and defined valid gaps as promoted canonical directions.
- Tests: evaluation schema and all three deterministic benchmark reports were regenerated outside the repository.
- Actual output inspected: recurring drift now reports 50 evidence events → 36 raw instances → 3 canonical families → 3 promoted directions, with 1 strong alignment and 3 final ideas.
- Score before: 4, 3, 2, 2, 4, 3, 4, 5.
- Score after: 5, 4, 5, 5, 4, 5, 4, 5.
- Remaining issue: missingness had no promoted direction because a valid family-level binding was discarded.
- Next decision: preserve explicit family constraints without claiming exact method evidence.

## Extended cycle 4 — family-level missingness binding (2026-08-01)

- Problem: the missingness benchmark had 18 raw gaps and 2 canonical families but zero promoted directions.
- Root cause: the compact algorithm library lacked the selected generic `tree ensemble` family, and extraction converted it to `unspecified`.
- Repair: preserve a user-selected generic family and infer only a failure-compatible modification slot; benchmark purposes now carry their declared allowed families.
- Tests: generic family/slot regression and evaluation harness passed.
- Actual output inspected: missingness changed from 0 to 2 promoted directions; it still correctly withheld candidates while no strong mechanism alignment existed.
- Score before: 2, 2, 4, 4, 4, 5, 2, 5.
- Score after: 4, 4, 4, 5, 4, 5, 4, 5.
- Remaining issue: the benchmark supplied immune/control evidence regardless of task and lacked a runnable family skeleton.
- Next decision: correct the benchmark evidence, not the alignment threshold.

## Extended cycle 5 — missingness mechanism validity (2026-08-01)

- Problem: missingness had no strong alignment or candidate even after direction binding.
- Root cause: external fixtures were unrelated to missing-feature observation, and no tree-ensemble skeleton owned the documented failure.
- Repair: added task-appropriate observability/predictive-correction fixtures, inference-available signals, and a missingness-aware tree-ensemble skeleton with feature-acquisition/routing slots.
- Tests: algorithm library, extraction, evaluation, and candidate audits passed.
- Actual output inspected: missingness now reports 2 promoted directions, 2 operational mechanisms, 1 strong alignment, 2 candidate drafts, and 2 falsifiable ideas.
- Score before: 4, 3, 4, 4, 4, 5, 3, 5.
- Score after: 5, 5, 4, 5, 4, 5, 5, 5.
- Remaining issue: dynamic clustering evaluated only the first promoted direction and missed a lifecycle-compatible path.
- Next decision: evaluate the full promoted portfolio without weakening validation.

## Extended cycle 6 — promoted-portfolio alignment evaluation (2026-08-01)

- Problem: dynamic clustering showed zero strong alignments even though a promoted component-lifecycle gap aligned with operational phase-transition and niche mechanisms.
- Root cause: the benchmark aligned mechanisms only to the first promoted/raw gap, which was a coverage gap rather than the lifecycle direction.
- Repair: audit all promoted representative gaps, select the strongest accepted typed path for candidate evaluation, use task-appropriate external fixtures, and add a bounded model-selection operator so the second production direction has a concrete rule rather than a dead end.
- Tests: evaluation harness, two complete AppTest direction paths, diagram failure fallback, and secret-loading tests cover the final behavior.
- Actual output inspected: dynamic clustering reports 3 promoted directions, 3 operational mechanisms, 1 strong alignment, 1 candidate draft, and 1 final idea. Missingness remains 2/2/1/2; recurring drift remains 3/3/1/3. Two UI directions both reach Part 3; the second now changes Gaussian Process model selection with a bounded recent-loss verification rule.
- Score before: 4, 3, 4, 4, 4, 5, 3, 5.
- Score after: 5, 5, 5, 5, 4, 5, 5, 5.
- Remaining issue: complete full-suite, clean archive, local launch, live anonymous probe, and bounded production verification.
- Next decision: no model adoption; measured problems were orchestration and benchmark validity, not representation quality.

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
