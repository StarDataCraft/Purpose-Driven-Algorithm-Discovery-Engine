# Overnight baseline — 2026-07-31

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
