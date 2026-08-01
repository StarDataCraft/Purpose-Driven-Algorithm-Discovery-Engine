# Architecture

Presentation uses `candidate_modification()` as the canonical slot-aware view of an algorithm delta. It selects objective, update, memory, routing, aggregation, initialization, stopping, or lifecycle changes from the actual affected component.

`openalex_client.py` owns the shared HTTP session, serialized limiter, credential attachment, typed rate-limit state, daily/transient 429 classification, retry policy, circuit breaker, and run-scoped query budgets. `retrieval_service.py` owns stable cache identity and source isolation. External retrieval begins with no more than three native domains and two queries per domain; ML slots are introduced only during structural alignment.

## Calibrated evidence and provenance

Each operation records a stage-scoped `StageRun`; query/source counts,
wall-clock and request durations, cache ages, inputs, outputs, acceptances, and
rejections retain their scope. Automatic relevance never writes human labels.
Gap evidence progresses through evidence events, raw instances, canonical
families, and promoted gaps.

## Presentation architecture

`ux_models.py` maps existing records into `DirectionSummary`,
`IdeaDerivation`, and `IdeaExplanation` without changing retrieval or scientific
scores. `diagram_builders.py` creates deterministic DOT and text-fallback
specifications without Streamlit or generative dependencies. State invalidation
is downstream-only for purpose, direction, and idea changes.

`external_discovery_pipeline.py` owns direction-scoped translation, retrieval,
mechanism extraction, and hard structural alignment. `idea_pipeline.py`
composes that result with the existing candidate search and portfolio selector.
Both are Streamlit-independent and join results to the parent ResearchRun with
parent-run, direction, gap, and inherited SearchPolicy identity.

## Capability modes

- `lightweight` (default): TF-IDF, deterministic extraction, coverage matrices,
  predicate assumptions, weak supervision, clustering, and the existing graph/search pipeline.
- `enhanced`: requests local SPECTER2 and falls back to lightweight if loading fails.
- `full`: enhanced retrieval plus a locally fine-tuned SciBERT classifier when a valid
  checkpoint is supplied. Without a checkpoint it uses weak supervision and rules.

Transformer libraries are imported only inside lazy model loaders. Core Streamlit startup
does not download models.

## Evidence pipeline

```text
PurposeContract
→ lexical paper queries
→ OpenAlex/arXiv retrieval and deduplication
→ TF-IDF sparse reranking
→ optional local SPECTER2 reranking (RRF)
→ agglomerative research clusters
→ coverage records and sparse cubes
→ relevance-aware coverage omissions
→ typed observed conditions
→ assumption predicate contradictions
→ explicit/weak-supervision sentence evidence
→ repeated and contradictory evidence
→ unified GapSignature
→ known-solution triage
→ existing mechanism alignment and candidate synthesis
```

## Phase 1

`coverage_analysis.py` records known/unknown dimensions with per-field provenance and
confidence. Sparse dictionary cubes avoid dense tensors. Coverage omissions require cluster
support, comparable neighboring cells, purpose relevance, metadata completeness, and an
executable evaluation.

`assumption_analysis.py` loads algorithm-specific, contextual assumptions and matches their
normalized predicates against evidence-backed conditions. Variant exceptions suppress false
mismatches. `contradiction_analysis.py` compares claims only when task, algorithm family,
failure, metric, and protocol are sufficiently compatible.

## Phase 2

`scientific_embeddings.py` implements a shared backend interface, TF-IDF fallback, lazy
SPECTER2 loader, and content-addressed SQLite cache. `hybrid_retrieval.py` uses reciprocal
rank fusion:

`1/(60 + sparse_rank) + 1/(60 + dense_rank)`.

Dense terms are omitted—not set to zero—when unavailable. `paper_clustering.py` uses
cosine agglomerative clustering with a distance threshold. `semantic_gap_aggregation.py`
requires structural compatibility in addition to embedding similarity.

## Phase 3

`weak_supervision.py` emits weighted, conflicting, multi-label votes.
`sentence_classifier.py` provides rule, fine-tuned SciBERT, and hybrid backends. Base
SciBERT is never presented as a trained classifier. Context windows preserve section,
previous, target, and next sentences. `annotation_schema.py` and Research Tools
UI support bounded human review and JSONL/CSV export.

## Persistence and bounds

Research-memory schema version 3 adds append-only versioned `ResultAudit` records without
removing legacy tables. Runtime DBs and embedding/model caches are ignored. Fetch, embedding,
sentence, graph, annotation, and cache sizes are bounded in `config.py`.

## Canonical retrieval and provenance

`retrieval_service.retrieve_corpus` is the live/cache/fixture mode resolver.
It writes retrieval events onto `Paper` records and then derives actual mode
from those events. `ResearchRun` and `SourceRetrievalResult` are the shared
typed contracts for all UI pages and persisted research memory.

The production literature path is:

`PurposeContract → problem queries → live/cache retrieval → deduplication →`
`sparse relevance → clustering → algorithm binding → focused retrieval →`
`structural discovery`.

The external path continues:

`selected GapSignature → CrossDomainProblemSignature → ranked domains →`
`native query profiles → external retrieval → mechanism extraction`.

Query validation bounds length, removes duplicates, and rejects malformed or
unsupported terms. Algorithm bindings record mentions, paper/source support,
relevance, method, confidence, and evidence. Low-confidence evidence stays at
family or `Unspecified` level.

The live response cache has a one-day TTL and stores successful live results
only. Force-fresh bypasses reads but never rate limiting. A failed new action
does not mutate the previously successful session-state run.

Purpose submission invalidates all downstream stage state. Selecting a
different gap invalidates external papers, mechanisms, alignments, direction
families, and candidates. Candidates and external stages retain the parent
research run ID.

## Evaluation layer

The `evaluation/` package observes the existing production pipeline; it does
not replace it. Versioned tasks and optional human annotations feed:

`retrieval metrics → query contribution → evidence/gap audits → coverage and`
`mismatch audits → binding/known solutions → external queries → mechanisms →`
`typed alignment → candidate rubric → stage funnel → error distribution`.

Reports include run/commit/task/query/domain/annotation versions, corpus
fingerprint, random seed, active model status, and thresholds. Research Memory
stores optional `HumanReview` records separately from generated artifacts. Complete
candidates additionally pass through ten independent 0–5 dimensions, adversarial
counterfactual status, and a self-critique. Any failed dimension makes the final
decision exploratory; automatic scores never masquerade as human review.

The only production repair justified by the initial synthetic baseline adds a
controlled structural-topology feature to alignment. Shared words alone still
cannot create a strong match; topology, compatible modification slot, evidence,
and absence of information conflicts are required. Two evaluator corrections
recognize aggregation/objective modifications and avoid calling an
unannotated insufficient search a known-solution miss.
