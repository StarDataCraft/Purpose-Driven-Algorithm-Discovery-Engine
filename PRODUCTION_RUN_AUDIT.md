# Baseline audit of the reported production ResearchRun

Audit date: 2026-07-31  
Baseline commit: `4eb47407366cd1aa2806dac5c11bbd349f2584c1`  
Baseline tests: `91 passed in 34.37s`

The original live paper corpus and response cache were not committed, so the
reported run cannot be replayed byte-for-byte. This audit distinguishes facts
proven by the current call graph from counts that cannot be reconstructed.

## Why 80 deduplicated papers became 80 “relevant” papers

`ResearchRun.finalize_from_papers()` set:

```python
self.deduplicated_paper_count = len(papers)
self.relevant_paper_count = len(papers)
```

No relevance threshold or human review was consulted. The value meant
“retained after deduplication,” not “relevant.” This is the exact cause.

## Why Transformer, CNN, Random Forest, and AdaBoost could be focused

`detect_algorithm_bindings()` searched each title and abstract for an
algorithm name or alias. Every matching paper counted as direct evidence,
including background lists, surveys, or comparison baselines. Confidence was:

`0.25 + 0.15 × direct-paper count + 0.08 × alias-paper count + 0.08 × source count`

It did not require a same-sentence target-failure link, task compatibility,
estimated relevance, title/evaluated-method context, or coherent clusters.
`generate_focused_algorithm_queries()` then selected the four highest
bindings above `0.45`, yielding eight queries. Therefore Transformer and CNN
could outrank task-native online methods through incidental mentions.

The original paper windows were not persisted, so the exact sentences that
triggered each binding cannot be recovered from the reported run.

## Why 121 gaps were presented

`discover_structural_gaps()` concatenated:

1. explicit sentence instances;
2. repeated instances;
3. coverage instances;
4. assumption-mismatch instances;
5. contradiction instances.

It computed semantic families but returned the raw concatenated `gaps` list to
the main selector. No promotion gate or bounded family portfolio existed.
Thus `structural_gap_count=121` meant raw heterogeneous instances, not 121
distinct research gaps.

The run stored only the total count. It did not persist per-type counts,
evidence-event counts, semantic-family membership, or promoted-gap counts.
Consequently the exact original 121-item type breakdown is unrecoverable
without the original corpus. Reconstructing one would be fabrication.

## Why warnings were empty

Warnings were emitted only for invalid settings, missing provenance, explicit
fixture fallback, or a model exception. There were no ratio or consistency
checks for all-retained-as-relevant, gaps per paper, weak exact bindings,
cache-only external evidence, evidence scarcity, or lack of strong
alignments. The reported ratios therefore could not create warnings.

## Provenance inconsistencies

- `query_count` was initialized from broad queries only; focused queries were
  appended later without updating it.
- `source_count` meant unique paper source names, while `source_results`
  contained repeated results across broad/focused calls.
- `retrieval_duration_seconds` belonged to one retrieval invocation, not the
  complete broad-plus-focused workflow.
- `cache_age_seconds` retained only the maximum age encountered.
- Cache hits could have `request_count=0`, returned papers, and an empty
  `api_status`.
- External retrieval stored only mode, paper count, and sources in
  `stage_records`; domain/query/cache/paper/mechanism-bearing detail was lost.
- `relevant_paper_count`, gap type counts, family counts, promotion counts,
  and human-review counts could not be audited later.

## External 60-paper cache result

The current code can obtain 60 external papers by executing all selected
domain queries through `retrieve_corpus(maximum_total=60)` and satisfying them
from fresh per-query cache entries. The reported `CACHE` mode proves current
paper origins were cached live results. It does not identify which
domain/query produced each retained paper in the stage summary.

Exact freshness cannot be reconstructed. The run retained a single maximum
cache age and one last cache timestamp rather than newest/oldest/median ages
and per-entry metadata. Any more precise claim would be unsupported.

## Baseline call graph

`PurposeContract → broad queries → retrieve/cache/deduplicate → name-based`
`binding → focused queries → second retrieval → combined deduplication →`
`sparse/optional dense reranking → clustering → raw gap extraction → known`
`solution checks → raw gap selector → external queries/retrieval → mechanism`
`extraction → alignment → candidate search → portfolio`

This document records the baseline before production behavior is changed.
