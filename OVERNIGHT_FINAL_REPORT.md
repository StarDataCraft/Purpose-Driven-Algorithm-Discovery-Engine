# Overnight final report — 2026-07-31

1. Starting commit: `87b8cfb3d5fa02de19ed760c7ef3d9fef0bdf856`.
2. Backup branch: `backup/pre-overnight-20260731`, pushed at the starting commit.
3. Working branch: `overnight/usability-science-20260731`.
4. Baseline tests: 106 passed in 106.34 seconds; compile, import, deployment smoke, health, and root HTTP passed.
5. Baseline failures: aggregation candidates showed an empty Change; proposal sections and typed mechanism mappings were incomplete; primary values were often JSON-like.
6. Root causes: the UI read only `update_rule_delta` instead of the delta for the affected slot; result layout and diagram builders omitted required typed fields.
7. Improvement cycles: 2 focused observe–repair–test–inspect cycles.
8. Part 1: paper roles distinguish direct evidence from contextual support; direction cards use readable field rows.
9. Part 2: candidate changes are slot-aware; gap, domain, retrieval, mechanism, alignment, and candidate summaries use readable fields; automatic external orchestration is preserved.
10. Part 3: explicit Problem, Current behavior, Proposed change, Expected result, and Closest known methods sections were added; exact slot/state/trigger/rule/inference information is visible.
11. External orchestration: retained the direction-scoped Streamlit-independent pipeline and verified live, mixed, cache, fixture, partial-source, zero-mechanism, and zero-alignment behavior in tests.
12. State invalidation: unchanged; AppTest verifies purpose changes, same-direction reuse, and different-direction invalidation/rebuild.
13. Readability: primary proposal content no longer depends on raw JSON; structured technical JSON remains in its expander.
14. Diagrams: evidence-to-idea now has seven stages; mechanism transfer separately maps signal, state, trigger, response, and risk; four deterministic diagrams retain text fallbacks.
15. Error states: existing stage-specific external retrieval, mechanism, alignment, and cache-miss recovery behavior remains covered; no duplicate failure was introduced.
16. Retrieval quality: synthetic benchmark Precision@10 is 0.5 for recurring drift, 0.5 for missingness shift, and 0.6 for dynamic clustering. These are fixture metrics, not whole-literature recall.
17. Gap quality: consolidation remains bounded; the visible offline run produced two promoted directions. Direct-paper counts are separated from contextual papers.
18. Mechanism quality: offline flow produced operational signatures with signal, state, trigger, response, constraint, target, and failure boundary.
19. Alignment quality: recurring drift has one strong synthetic alignment after the existing repair; missingness and clustering still report alignment as their dominant benchmark bottleneck.
20. Candidate quality: displayed changes are non-empty and selected from the actual modification slot; exact slot, information requirements, risk, experiment, and kill criterion are visible.
21. Open-source models evaluated: none downloaded during this cycle.
22. Model benchmark: not applicable; the measured bottleneck was deterministic field selection and presentation.
23. Models adopted: none.
24. Models rejected: none downloaded; adding an encoder was rejected as irrelevant to the measured defect and unnecessary deployment cost.
25. Lightweight performance, one AppTest offline run: Part 1 0.0654 s, Part 2 0.0784 s, diagrams 0.0001 s, Part 3 render 0.0002 s. These are local measurements, not production latency.
26. Enhanced performance: not tested; no enhanced model was loaded and no enhanced success is claimed.
27. Tests added: slot-aware delta selection, complete diagram fallback roles, non-empty candidate changes, and explicit Part 3 proposal sections.
28. Final pytest: 108 passed in 107.49 seconds in the working tree.
29. AppTest: primary startup and all three-part workflow tests passed within the full suite; focused suite was 17 passed.
30. Clean tree: archived checkpoint passed import, deployment smoke, and 108 tests in 108.35 seconds.
31. Local Streamlit: lightweight startup succeeded; `/_stcore/health` and root returned HTTP 200; startup log contained no exception.
32. Production verification: bounded verification occurs after the final main push. HTTP health can be checked directly; visible build identity cannot be claimed if browser automation or deployment logs are unavailable.
33. Remaining scientific limitations: automatic relevance is not human review; fixture evidence is not current literature; heuristic alignment does not establish novelty, correctness, or performance; missingness and dynamic-clustering alignment remain benchmark bottlenecks.
34. Remaining deployment limitations: optional enhanced models were not loaded; Streamlit propagation timing and server-side deployment logs are outside the repository test environment.
35. Final commit SHA: authoritative value is `git rev-parse HEAD` after the report commit and main merge.
36. Push result: authoritative result is the final normal `git push origin main`; no force push is used.
37. Final status: must be clean with local `HEAD` equal to `origin/main` before completion.

## Acceptance decision

All locally verifiable mandatory gates pass at the working-branch checkpoint. The final merge gate requires updating from `origin/main`, rerunning verification, merging to main, pushing, and checking the production endpoint without overstating visible-build verification.
