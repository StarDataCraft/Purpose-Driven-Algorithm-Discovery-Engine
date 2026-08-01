# Targeted non-generative state-of-the-art review

Review date: 2026-08-01. Sources were checked through this date. “State of the art” is not claimed for the application: the project lacks a sufficiently large, human-reviewed held-out corpus on which to establish that claim.

## Observed bottleneck and baseline

The new ten-angle audit identifies human-reviewed evidence validity and known-solution coverage as the shared blocking dimensions across all three synthetic benchmarks. The existing deployment-safe baseline is sparse TF–IDF plus deterministic field/rule checks. Synthetic retrieval metrics are Precision@10 0.50/0.50/0.60 and nDCG@10 1.000/0.9054/0.9882 for recurring drift, missingness shift, and dynamic clustering respectively. These are CI-fixture measurements, not live-literature or model-quality evidence.

No model was downloaded or adopted. There is no held-out paper-level review set suitable for a defensible before/after model comparison, so downloading a model would violate the adoption gate rather than resolve it.

## Shortlist (three methods)

### 1. SPECTER2 with the ad-hoc query/search adapter

- Primary sources: [official SPECTER2 repository](https://github.com/allenai/SPECTER2), [official model card](https://huggingface.co/allenai/specter2_base), and the linked SciRepEval work.
- Release: 2023 model-card update; SciRepEval publication 2022.
- Exact task: scientific document representation, proximity retrieval, and ad-hoc scientific search using task-specific adapters.
- Architecture: non-generative BERT/SciBERT-family encoder with adapters; base-card parameter count is not explicitly stated, so this review does not invent one.
- Execution: local; CPU feasible for bounded top-K reranking, with expected hundreds of MB of weights and materially higher cold-start/latency than TF–IDF. Exact memory and latency were not measured because no download occurred.
- License: Apache-2.0.
- Training/annotations: pretrained, but this application still needs reviewed relevance labels to select an adapter, tune fusion, and evaluate Precision@5/10/20 and nDCG.
- Evidence: trained on more than six million citation triplets and evaluated on SciRepEval according to the official model card.
- Relevance: strongest shortlist candidate for the paper-ranking bottleneck, using the correct ad-hoc query adapter for queries and proximity adapter for candidates.
- Decision: **defer**. Do not enable in production until it beats sparse retrieval on a paper-level held-out set across at least two tasks without unacceptable cold start.

### 2. SciNCL

- Primary sources: [EMNLP 2022 paper](https://aclanthology.org/2022.emnlp-main.802/) and [official model card](https://huggingface.co/malteos/scincl).
- Release: February/December 2022.
- Exact task: citation-neighborhood contrastive scientific document representation.
- Architecture: non-generative BERT encoder; official model card reports approximately 0.1B parameters.
- Execution: local; CPU feasible for bounded top-K encoding, likely hundreds of MB resident memory. Exact application latency/memory were not measured.
- License: MIT.
- Training/annotations: pretrained from citation neighborhoods; application-specific reviewed relevance and known-solution references remain necessary.
- Benchmark evidence: the paper reports improvement on SciDocs; that does not establish improvement on this project’s three tasks.
- Relevance: plausible citation-aware alternative for document similarity and foundational-paper expansion.
- Decision: **reject for this cycle**. It overlaps SPECTER2’s target stage and no reviewed corpus supports a fair two-model experiment; SPECTER2’s explicit ad-hoc search adapter is the better first test.

### 3. MultiVerS

- Primary sources: [NAACL Findings 2022 paper](https://aclanthology.org/2022.findings-naacl.6/) and [official repository](https://github.com/dwadden/multivers).
- Release: July 2022; training code update January 2023.
- Exact task: scientific claim support/refutation plus evidence-rationale selection using full-document context.
- Architecture: non-generative Longformer-based multitask classifier/rationale selector.
- Execution: local; CPU operation is possible in principle but a Longformer-large checkpoint is unsuitable for lightweight cold starts. Parameter count, checkpoint bytes, memory, and application latency were not documented in the inspected sources and were not measured.
- License: MIT for the official repository.
- Training/annotations: pretrained checkpoints target SciFact, CovidFact, and HealthVer. The repository explicitly describes the software as a research prototype; domain transfer requires labeled claims/rationales or careful weak supervision.
- Benchmark evidence: the paper reports gains on three scientific claim-verification datasets, especially zero/few-shot adaptation; this is supporting evidence only, not permission to auto-promote a gap.
- Relevance: could rank supporting/contradicting sentences and audit known-solution claims after retrieval.
- Decision: **defer**. It is too heavy for default deployment and the project lacks claim-level labels; it may later operate only in enhanced mode and may never override hard promotion rules.

## Bounded experiment decision

| Item | Result |
|---|---|
| Models considered | SPECTER2, SciNCL, MultiVerS |
| Models downloaded | None (0 GB) |
| Models deeply benchmarked | None; no reviewed evaluation set exists |
| Models adopted | None |
| Production use | Existing lightweight sparse/rule pipeline only |
| Enhanced-mode change | None |
| Actual added memory | 0 MB |
| Actual added model latency | 0 ms |

The next scientifically valid experiment is to review the top 20 results, known-solution references, and evidence sentences for at least two tasks; freeze those labels; then compare sparse TF–IDF against SPECTER2 ad-hoc/proximity scoring and reciprocal-rank fusion. Required metrics are Precision@5/10/20, nDCG@10/20, evidence-bearing papers in the top 20, known-solution recall, CPU latency, peak RSS, and cold start. MultiVerS should be evaluated only after claim/rationale labels exist.

## Adoption guardrails

- Dense or claim models may rank compatible records but may not override training/inference scope, information availability, algorithm-family, failure-topology, or modification-slot constraints.
- Automatic relevance is not human relevance.
- A model may be adopted only after an identical held-out before/after comparison, improvement on two tasks (or explicit task-specific evidence), no safety regression, acceptable CPU cost, and an intact lightweight fallback.
