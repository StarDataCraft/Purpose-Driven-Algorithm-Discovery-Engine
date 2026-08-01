# Overnight baseline

## Extended cycle — 2026-08-01

- Starting commit: `e5f7942217ce6943d1cf80d52cfa202e2e250427`.
- Safety branch: `backup/pre-autonomous-cycle-20260801`.
- Working branch: `overnight/autonomous-quality-20260801`.
- Repository was clean on `main`; origin matched the required GitHub URL.
- Baseline compile, import, and deployment smoke passed. The inherited suite contained 108 tests and passed before the cycle.
- The three-part deterministic workflow was operational, but OpenAlex had no canonical client, shared limiter, typed quota state, query budget, or circuit breaker.
- A 429 was treated by the generic request retry loop; later queries continued and could create a request storm.
- Each unbound request could create a new `requests.Session`.
- External retrieval generated up to five domains and all templates, then appended the ML slot (for example `aggregation`) to native-domain queries.
- Failure messages accumulated per query and were also repeated in the sidebar as raw JSON.
- OpenAlex `per-page` followed the small per-query UI value rather than retrieving a useful candidate pool in one call.
- The runtime process had no `OPENALEX_API_KEY`; anonymous behavior was not explicitly budgeted or explained.
- No supplied credential was written, printed, serialized, or added to Git configuration.

### Baseline scientific and deployment concerns

- Exhaustive external fan-out spent requests without evidence-based stopping.
- Rate-limit failure could make Part 2 unusable even when arXiv remained available.
- OpenAlex cache keys did not record selected fields or query-profile version.
- Production still redirects unauthenticated inspection to Streamlit login, so visible build verification remains constrained.

## Prior cycle — 2026-07-31

Starting commit: `87b8cfb3d5fa02de19ed760c7ef3d9fef0bdf856`

Safety branch: `backup/pre-overnight-20260731`

Working branch: `overnight/usability-science-20260731`

## Engineering baseline

- `python -m pytest -q`: 106 passed in 106.34 seconds.
- `python -m compileall -q .`: passed.
- `python -c "import app"`: passed, with Streamlit's expected bare-mode context warning.
- `python scripts/deployment_smoke_test.py`: passed.
- Lightweight Streamlit: health endpoint HTTP 200 and root HTTP 200 on port 8765; no startup exception.
- Primary navigation contained exactly Discover directions, Analyze the gap, and Explain the idea.

## Reproduced workflow

The deterministic offline path completed all three parts without an exception: find directions, select a direction, derive ideas with automatic external evidence, select an idea, and render its explanation with four diagrams. Direction changes invalidated dependent state and Part 2 rebuilt it. No removed Step 4 instruction appeared.

## Baseline user-facing failures

- Part 2 read only `update_rule_delta` for “Change”. Aggregation candidates therefore displayed an empty change even though `aggregation_delta` held a formula.
- Part 3 omitted explicit Problem, Current behavior, Proposed change, Expected result, and Closest known methods sections.
- The mechanism-transfer diagram compressed signal, state, trigger, response, and risk instead of showing five correspondences.
- Primary pages rendered many dictionaries and lists as JSON-like blocks.
- Paper roles did not explicitly distinguish contextual support from direct gap evidence.

## Scientific and deployment risks

- Relevance is automatic unless explicitly reviewed; synthetic benchmark labels are not human review.
- Offline fixtures cannot establish literature currency or novelty.
- Cross-domain alignment is a deterministic heuristic, not evidence that a translated algorithm will work.
- Public lightweight mode intentionally avoids optional transformer imports.
- Production propagation and build identity require verification after the final main push.

No API dumps, caches, databases, weights, exports, or screenshots belong in the repository.
