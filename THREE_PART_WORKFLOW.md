# Three-part research workflow

Part 3 explicitly renders Problem, Current behavior, Proposed change, Expected result, closest methods, risks, uncertainty, supporting papers, and the minimum experiment. The proposed change exposes the exact slot, new state, trigger, rule, and inference-time information before technical details.

Part 2 treats OpenAlex and arXiv independently. If OpenAlex reaches a daily or short-term limit, its circuit stops later calls while arXiv and permitted cache entries continue. The page shows one concise source-status message; request-level details remain under Technical diagnostics.

The primary interface presents the unchanged scientific pipeline in three
researcher-oriented parts.

## 1. Discover directions / 发现方向

This combines the former Goal Setup, paper retrieval, Gap Radar, and Gap
Evidence screens. One search action produces typed `DirectionSummary` records
and related papers grouped by evidence role. Selecting a direction freezes its
direction and gap identifiers, preserves the corpus and `ResearchRun`, and
invalidates only downstream mechanism and idea state.

## 2. Analyze the gap / 分析 Gap

This combines external-mechanism search, gap detail, known-solution search,
structural alignment, and direction families. Paper-stated evidence stays
separate from system inference. The derivation is:

`gap → required capability → external analogue → mechanism → correspondence → modification slot → idea`

Mechanisms retain signal, state, trigger, response, constraint, and failure
boundary. Candidate ideas retain the selected-gap snapshot and alignment path.

The Part 2 action automatically translates the selected gap, selects external
domains, retrieves their literature, extracts operational mechanisms, enforces
structural alignment, and synthesizes the portfolio. It inherits Part 1's
search policy: LIVE remains live-first, CACHE requires a matching cache and
offers an explicit live retry on a miss, and OFFLINE_FIXTURE remains visibly a
demonstration. Fixtures never silently replace live evidence.

External results are keyed by parent run, direction, gap, and policy. Selecting
a different direction clears them; reselecting the same direction reuses a
matching session result. Zero-mechanism and zero-alignment outcomes show stage,
evidence, rejection, and recovery details without lowering hard thresholds.

## 3. Explain the idea / 解释新想法

This combines candidate details, novelty/falsification, minimal experiment, and
the Research Result. It begins with one qualified conclusion and displays
`BEFORE → CHANGE → EXPECTED RESULT`, the exact modification slot, risks,
supported/inferred/unknown claims, supporting papers, and a kill criterion.

Four deterministic DOT diagrams cover evidence flow, before/change/expected
result, mechanism transfer, and experiment design. Every diagram includes a
text fallback. No image-generation or generative language model is used.

Changing only the selected idea regenerates the explanation and diagrams while
preserving upstream evidence.

## Research Tools / 研究工具

The collapsed technical section preserves ResearchRun and StageRun provenance,
retrieval diagnostics, coverage and evidence audits, alignments, quality
evaluation, annotation tools, Research Memory, raw JSON, and build identity.
These tools do not gate the primary workflow.

## Exports and uncertainty

Part 3 exports readable Markdown, structured JSON, DOT diagrams, and experiment
Markdown. Automatic relevance remains separate from human review; paper claims
remain separate from inference; novelty and expected improvement remain
unverified until external evaluation.
## Atomic Part 2 → Part 3 selection

Part 2 presents one candidate-ID-backed radio selector, a visible selected-idea
summary, and one `Continue to explanation` button. The normal render branch
resolves and validates the candidate, derivation, direction, gap, and parent
run, stores a plain versioned `SelectedIdeaContext` dictionary, verifies the
stored identities, and performs exactly one rerun into Part 3. Candidate domain
objects are never passed through a button callback.

Part 3 reconstructs its inputs from the context snapshots first. Mutable Part 2
portfolios are used only to recover an older ID-only session, and successful
recovery is immediately upgraded to a context. Back navigation retains the
portfolio and context. A purpose, run, direction, or gap change invalidates the
context; selecting another idea in the same portfolio replaces only Part 3
products.

Manual Part 3 navigation is guided back to the missing prerequisite. When ideas
exist but none is selected, Part 3 presents the same compact selector inline.
