# Architecture

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
previous, target, and next sentences. `annotation_schema.py` and the Step 2 Research Tools
UI support bounded human review and JSONL/CSV export.

## Persistence and bounds

Research-memory schema version 2 adds generic structural/model records without removing
legacy tables. Runtime DBs and embedding/model caches are ignored. Fetch, embedding,
sentence, graph, annotation, and cache sizes are bounded in `config.py`.
