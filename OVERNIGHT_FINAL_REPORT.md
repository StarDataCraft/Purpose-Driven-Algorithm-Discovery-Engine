# Autonomous engineering final report — 2026-08-01

1. Starting commit: `e5f7942217ce6943d1cf80d52cfa202e2e250427`.
2. Backup branch: `backup/pre-autonomous-cycle-20260801`, pushed at the starting commit.
3. Working branch: `overnight/autonomous-quality-20260801`.
4. Total continuous execution time: approximately 11 hours from baseline capture through final local verification; Git records the first repair checkpoint at 09:07 JST after the prior 22:40 JST baseline commit.
5. Completed cycles: 6 extended observe–repair–test–inspect cycles.
6. Baseline tests: the inherited 108-test suite passed; compile, import, deployment smoke, health, and the deterministic three-part workflow also passed.
7. Baseline failures: OpenAlex lacked a shared limiter, typed quota state, circuit breaker, and run budget; a 429 could fan out into later requests; external queries mixed native-domain terms with ML slots; scientific funnel counts overstated production gaps; missingness and dynamic clustering had avoidable benchmark dead ends.
8. Root causes: source-generic request handling, exhaustive query fan-out, conflated detector-event/direction counts, discarded family-level constraints, task-irrelevant benchmark evidence, and evaluation of only the first promoted gap.
9. OpenAlex key mode tested: API-key behavior is covered with synthetic test credentials only. The supplied credential was not written, printed, committed, or used from the shell; the live probe therefore exercised anonymous mode.
10. OpenAlex calls before repair: a daily-limit mock could retry and continue into later queries; the architecture had no run-level bound or circuit, so fan-out was query-count dependent.
11. OpenAlex calls after repair: daily-limit mock makes exactly 1 HTTP call and skips subsequent OpenAlex queries; a live anonymous probe made 1 successful OpenAlex request and returned 4 OpenAlex papers alongside 4 arXiv papers.
12. Budgets: API-key mode permits 30 total, with broad/focused/known/external/citation caps of 8/6/5/8/3; anonymous mode permits 12 total, with caps of 5/2/2/3/0.
13. Circuit breaker: daily quota exhaustion opens immediately; transient 429 honors `Retry-After`, retries at most three times, and then opens; typed diagnostics retain category/reset/skipped counts without request secrets.
14. Cache behavior: keys normalize query, source, publication window, selected-field profile, page size, and query-profile version; duplicate in-run requests coalesce; force-fresh bypasses response reuse; cache replay covers the complete bounded adaptive plan.
15. arXiv continuation: an OpenAlex circuit/error does not stop arXiv; the regression suite verifies retained arXiv evidence.
16. Part 1 changes: purpose contracts retain declared families and task-specific inference information; the honest funnel distinguishes evidence events, raw instances, canonical families, and promoted directions.
17. Part 2 changes: external Stage 1 uses at most three domains and two native queries each; conditional Stage 2 adds at most four queries only when evidence/mechanism sufficiency is not reached; all retrieval shares one OpenAlex client and run budget.
18. Part 3 changes: a bounded model-selection operator gives the second tested direction a concrete verification rule, while exact modification, inference requirements, risk, experiment, and kill criterion remain visible.
19. Readability changes: the UI presents one concise OpenAlex state/warning, keeps source detail in the technical expander, and avoids duplicated raw failure JSON.
20. Diagram changes: both tested direction paths retain four deterministic diagrams; diagram-generation failures retain complete text fallbacks.
21. Error-state changes: daily and transient limits are distinct; circuits stop request storms; cache miss, no mechanism, no alignment, and source failure remain explicit and recoverable; no silent fixture fallback was added.
22. Retrieval-quality findings: deterministic benchmark corpora retrieve 7 recurring-drift papers, 7 missingness papers, and 8 dynamic-clustering papers; the anonymous live probe returned 8 unique papers from two sources. These measurements do not establish literature recall.
23. Gap-quality findings: recurring drift produces 50 evidence events → 36 raw gaps → 3 families → 3 promoted directions; missingness 32 → 18 → 2 → 2; dynamic clustering 61 → 35 → 4 → 3.
24. Mechanism-quality findings: recurring drift yields 3 operational mechanisms, missingness 2, and dynamic clustering 3; each accepted mechanism retains signal, state, trigger, response, constraints, and failure boundary.
25. Alignment-quality findings: each benchmark now has 1 strong typed alignment after evaluating promoted representatives; alignment remains heuristic evidence, not proof of transfer validity.
26. Candidate-quality findings: recurring drift yields 3 drafts/3 final ideas, missingness 2/2, and dynamic clustering 1/1; two distinct AppTest direction paths reach complete Part 3 proposals.
27. Open-source models researched: no external model was required; the measured faults were deterministic orchestration, schema, and benchmark-evidence defects.
28. Models downloaded: none.
29. Models adopted: none.
30. Models rejected and why: model integration was rejected because it would not repair rate-limit control, funnel accounting, typed alignment coverage, or missing deterministic operators, and would add deployment cost.
31. Benchmark before/after: missingness improved from 0 promoted directions to 2 and from 0 strong alignments/final ideas to 1/2; dynamic clustering improved from 0 strong alignments/final ideas to 1/1; recurring drift reporting changed from 34 undifferentiated “valid gaps” to 3 promoted directions while retaining 1 strong alignment and 3 ideas.
32. Tests added: daily/transient 429 and circuit behavior, API-key redaction, anonymous budgets, arXiv continuation, duplicate-query coalescing, native external queries, adaptive Stage 2 and early stop, family/slot preservation, funnel accounting, two complete UI direction paths, and diagram fallback.
33. Final pytest result: 121 passed in 87.75 seconds in the working tree before the final commit.
34. AppTest result: startup, the primary page, full three-part workflow, state invalidation, and two distinct complete direction paths pass within the suite.
35. Clean-tree result: Git archive at checkpoint `6871d1f8cee7debd5f94491ea885dbfdcbcd56e3` passed 121 tests in 87.94 seconds, compile, archive-local import, and deployment smoke.
36. Local Streamlit result: headless launch on port 8765 succeeded; `/_stcore/health` returned `ok`, root returned HTTP 200, and the startup log contained no exception.
37. Production verification: no production URL is recorded in repository configuration, GitHub reports no deployments for the public repository, and bounded search found no matching Streamlit app. Direct production or visible-build verification is therefore not claimed.
38. Remaining scientific limitations: automatic relevance is not human review; fixture benchmarks cannot establish novelty or current whole-literature recall; deterministic mechanism alignment cannot establish empirical performance.
39. Remaining deployment limitations: production propagation and authenticated build logs are outside repository control; optional API-key mode depends on a runtime secret configured by the deployer.
40. Final commit SHA: authoritative value is `git rev-parse HEAD` after this report is committed and merged.
41. Push result: checkpoint `6871d1f8cee7debd5f94491ea885dbfdcbcd56e3` was fast-forwarded and pushed normally to `origin/main`; no force push was used. This evidence-only report update is pushed normally afterward.
42. Final Git status: verified after the report update; completion requires a clean `main` with local `HEAD` equal to `origin/main`.

## Acceptance decision

All locally verifiable scientific and engineering gates pass. The production build remains unverified because no deploy target is discoverable from the repository or public GitHub deployment metadata.

## Multi-angle result-audit cycle — 2026-08-01

The application now audits each displayed final idea from ten independent perspectives and persists immutable, version-comparable records in Research Memory. The visible **Critical review / 批判性审查** states the strongest case for and against the idea, likely duplicate, fragile evidence, uncertain mapping, and fastest invalidation experiment. Full scores, evidence, repairs, adversarial status, and raw records remain under Research Tools.

| Task | Original result | Main defect | Dimension | Repair | SOTA considered | Tested | Before | After | Cost | Decision | Limitation |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Recurring drift | Candidate generated | No human-reviewed evidence or sufficient prior-art search | Evidence; novelty | Ten-pass gate and counterfactual record | SPECTER2; MultiVerS | Deterministic audit | 0 final-result dimensions | 10 dimensions; scores 5/3/3/2/5/5/5/5/4/4 | 0 model MB | Exploratory | Synthetic P@10 0.50; no live prior-art recall |
| Missingness shift | Candidate generated | Same blockers; broad family binding | Evidence; novelty; specificity | Audit plus family counterfactual | SPECTER2; SciNCL | Deterministic audit | 0 dimensions | 10; 5/3/3/2/5/5/4/5/4/4 | 0 model MB | Exploratory | Synthetic P@10 0.50 |
| Dynamic clustering | Candidate generated | Prior-art search insufficient | Evidence; novelty | Audit plus mechanism and seed checks | SPECTER2; MultiVerS | Deterministic audit | 0 dimensions | 10; 5/3/3/2/5/5/4/5/4/4 | 0 model MB | Exploratory | Synthetic P@10 0.60 |

Models considered: SPECTER2 (Apache-2.0), SciNCL (MIT), and MultiVerS (MIT). Models downloaded/adopted: none. Download size, model RSS, and model latency are therefore 0; production and enhanced mode remain unchanged. Adoption was deferred because no sufficiently large human-reviewed paper/claim set exists for a defensible identical-corpus comparison. Detailed method metadata and decisions are in `SOTA_REVIEW.md`; measured audit and adversarial findings are in `MULTI_ANGLE_AUDIT_REPORT.md`.
