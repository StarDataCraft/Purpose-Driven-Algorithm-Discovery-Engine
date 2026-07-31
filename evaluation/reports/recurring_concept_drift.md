# Quality evaluation: recurring_concept_drift

> Automated quality metrics are meaningful only against reviewed annotations.
> The deterministic offline labels are synthetic CI fixtures, not scientific ground truth.

## Purpose

Benchmark version: `1.0.0`

## Run provenance

```json
{
  "active_engine_mode": "lightweight",
  "actual_search_mode": "LIVE",
  "annotations_version": "synthetic-ci-v1",
  "benchmark_task_version": "1.0.0",
  "domain_profile_version": "domain-translation-v1",
  "paper_corpus_fingerprint": "2f45041c9b3efa6b6d39d73914104d357bbe2dd1d526913fb9f03576684729db",
  "pipeline_version": "d6e2355a8c220f808644073dd7c146cbfef9a20f",
  "query_generator_version": "problem-query-v2",
  "random_seed": 47,
  "run_id": "evaluation:recurring_concept_drift:synthetic-ci-v1",
  "scibert_status": "not loaded",
  "sources": [
    "openalex",
    "arxiv"
  ],
  "specter2_status": "not loaded; NON-SCIENTIFIC fallback evaluation",
  "thresholds": {
    "binding_confidence": 0.45,
    "minimum_live_corpus_size": 8
  },
  "timestamp": "2026-07-31T00:00:00+00:00",
  "top_retrieved_papers": [
    {
      "paper_id": "synthetic:recurring_concept_drift:0",
      "relevance_label": "HIGHLY_RELEVANT",
      "source": "mock_openalex",
      "title": "[SYNTHETIC] adaptive random forest for recurring concept drift",
      "year": 2021
    },
    {
      "paper_id": "synthetic:recurring_concept_drift:1",
      "relevance_label": "HIGHLY_RELEVANT",
      "source": "mock_arxiv",
      "title": "[SYNTHETIC] adaptive random forest for concept recurrence",
      "year": 2022
    },
    {
      "paper_id": "synthetic:recurring_concept_drift:2",
      "relevance_label": "HIGHLY_RELEVANT",
      "source": "mock_openalex",
      "title": "[SYNTHETIC] adaptive random forest for post-drift recovery",
      "year": 2023
    },
    {
      "paper_id": "synthetic:recurring_concept_drift:3",
      "relevance_label": "HIGHLY_RELEVANT",
      "source": "mock_arxiv",
      "title": "[SYNTHETIC] adaptive random forest for adaptation delay",
      "year": 2024
    },
    {
      "paper_id": "synthetic:recurring_concept_drift:5",
      "relevance_label": "RELEVANT",
      "source": "mock_arxiv",
      "title": "[SYNTHETIC] Study of online classification",
      "year": 2021
    },
    {
      "paper_id": "synthetic:recurring_concept_drift:8",
      "relevance_label": "PARTIALLY_RELEVANT",
      "source": "mock_openalex",
      "title": "[SYNTHETIC] Broad online classification survey",
      "year": 2024
    },
    {
      "paper_id": "synthetic:recurring_concept_drift:10",
      "relevance_label": "IRRELEVANT",
      "source": "mock_openalex",
      "title": "[SYNTHETIC] Unrelated benchmark 10",
      "year": 2021
    }
  ],
  "working_tree_dirty": true
}
```

## Query set and contribution

- `online classification recurring concept drift` — broad; unique=7; relevant=5; labels=[]
- `online classification recurrent concept drift` — broad; unique=7; relevant=5; labels=[]
- `online classification concept recurrence` — broad; unique=7; relevant=5; labels=[]
- `online classification recurring regimes` — broad; unique=7; relevant=5; labels=[]
- `online classification recovery after concept drift` — broad; unique=7; relevant=5; labels=[]
- `online classification post-drift recovery` — broad; unique=7; relevant=5; labels=[]
- `stream classification recurring concepts` — broad; unique=7; relevant=5; labels=[]
- `online learning recurring contexts delayed labels` — broad; unique=7; relevant=5; labels=[]
- `tabular streams concept history reuse` — broad; unique=7; relevant=5; labels=[]
- `online classification worst-window accuracy after drift` — broad; unique=7; relevant=5; labels=[]

## Retrieval metrics

- precision_at_5: 1.0
- precision_at_10: 0.5
- precision_at_20: 0.25
- ndcg_at_10: 1.0
- ndcg_at_20: 1.0
- relevant_paper_count: 5
- highly_relevant_paper_count: 4
- source_diversity: 2
- year_coverage: 4
- duplicate_rate: 0.0
- abstract_availability: 1.0
- full_evidence_availability: 1.0

## Top retrieved papers and relevance labels

```json
[
  {
    "paper_id": "synthetic:recurring_concept_drift:0",
    "title": "[SYNTHETIC] adaptive random forest for recurring concept drift",
    "year": 2021,
    "source": "mock_openalex",
    "relevance_label": "HIGHLY_RELEVANT"
  },
  {
    "paper_id": "synthetic:recurring_concept_drift:1",
    "title": "[SYNTHETIC] adaptive random forest for concept recurrence",
    "year": 2022,
    "source": "mock_arxiv",
    "relevance_label": "HIGHLY_RELEVANT"
  },
  {
    "paper_id": "synthetic:recurring_concept_drift:2",
    "title": "[SYNTHETIC] adaptive random forest for post-drift recovery",
    "year": 2023,
    "source": "mock_openalex",
    "relevance_label": "HIGHLY_RELEVANT"
  },
  {
    "paper_id": "synthetic:recurring_concept_drift:3",
    "title": "[SYNTHETIC] adaptive random forest for adaptation delay",
    "year": 2024,
    "source": "mock_arxiv",
    "relevance_label": "HIGHLY_RELEVANT"
  },
  {
    "paper_id": "synthetic:recurring_concept_drift:5",
    "title": "[SYNTHETIC] Study of online classification",
    "year": 2021,
    "source": "mock_arxiv",
    "relevance_label": "RELEVANT"
  },
  {
    "paper_id": "synthetic:recurring_concept_drift:8",
    "title": "[SYNTHETIC] Broad online classification survey",
    "year": 2024,
    "source": "mock_openalex",
    "relevance_label": "PARTIALLY_RELEVANT"
  },
  {
    "paper_id": "synthetic:recurring_concept_drift:10",
    "title": "[SYNTHETIC] Unrelated benchmark 10",
    "year": 2021,
    "source": "mock_openalex",
    "relevance_label": "IRRELEVANT"
  }
]
```

## Gap extraction results

```json
[
  {
    "item_id": "agg:25c1dc1658c1",
    "label": "CORRECT",
    "reasons": [
      "evidence intersects reviewed relevant papers"
    ],
    "errors": [],
    "score_components": {
      "field_completeness": 1.0,
      "evidence_support": 1.0,
      "abstract_only": 0.0
    }
  },
  {
    "item_id": "mismatch:d19d170e0c66",
    "label": "CORRECT",
    "reasons": [
      "evidence intersects reviewed relevant papers"
    ],
    "errors": [],
    "score_components": {
      "field_completeness": 1.0,
      "evidence_support": 1.0,
      "abstract_only": 0.0
    }
  },
  {
    "item_id": "mismatch:d19d170e0c66",
    "label": "CORRECT",
    "reasons": [
      "evidence intersects reviewed relevant papers"
    ],
    "errors": [],
    "score_components": {
      "field_completeness": 1.0,
      "evidence_support": 1.0,
      "abstract_only": 0.0
    }
  },
  {
    "item_id": "mismatch:f04a142c21b2",
    "label": "CORRECT",
    "reasons": [
      "evidence intersects reviewed relevant papers"
    ],
    "errors": [],
    "score_components": {
      "field_completeness": 1.0,
      "evidence_support": 1.0,
      "abstract_only": 0.0
    }
  },
  {
    "item_id": "mismatch:f04a142c21b2",
    "label": "CORRECT",
    "reasons": [
      "evidence intersects reviewed relevant papers"
    ],
    "errors": [],
    "score_components": {
      "field_completeness": 1.0,
      "evidence_support": 1.0,
      "abstract_only": 0.0
    }
  },
  {
    "item_id": "mismatch:7904f504f472",
    "label": "CORRECT",
    "reasons": [
      "evidence intersects reviewed relevant papers"
    ],
    "errors": [],
    "score_components": {
      "field_completeness": 1.0,
      "evidence_support": 1.0,
      "abstract_only": 0.0
    }
  },
  {
    "item_id": "mismatch:7904f504f472",
    "label": "CORRECT",
    "reasons": [
      "evidence intersects reviewed relevant papers"
    ],
    "errors": [],
    "score_components": {
      "field_completeness": 1.0,
      "evidence_support": 1.0,
      "abstract_only": 0.0
    }
  },
  {
    "item_id": "mismatch:ad7a76edae51",
    "label": "CORRECT",
    "reasons": [
      "evidence intersects reviewed relevant papers"
    ],
    "errors": [],
    "score_components": {
      "field_completeness": 1.0,
      "evidence_support": 1.0,
      "abstract_only": 0.0
    }
  },
  {
    "item_id": "mismatch:ad7a76edae51",
    "label": "CORRECT",
    "reasons": [
      "evidence intersects reviewed relevant papers"
    ],
    "errors": [],
    "score_components": {
      "field_completeness": 1.0,
      "evidence_support": 1.0,
      "abstract_only": 0.0
    }
  },
  {
    "item_id": "mismatch:b6d21023b41b",
    "label": "UNSUPPORTED",
    "reasons": [],
    "errors": [
      "EVIDENCE_EXTRACTION_UNSUPPORTED"
    ],
    "score_components": {
      "field_completeness": 1.0,
      "evidence_support": 0.0,
      "abstract_only": 0.0
    }
  },
  {
    "item_id": "gap:98bc50ef1537",
    "label": "CORRECT",
    "reasons": [
      "evidence intersects reviewed relevant papers"
    ],
    "errors": [],
    "score_components": {
      "field_completeness": 1.0,
      "evidence_support": 1.0,
      "abstract_only": 0.0
    }
  },
  {
    "item_id": "gap:8ed5db679476",
    "label": "CORRECT",
    "reasons": [
      "evidence intersects reviewed relevant papers"
    ],
    "errors": [],
    "score_components": {
      "field_completeness": 1.0,
      "evidence_support": 1.0,
      "abstract_only": 0.0
    }
  },
  {
    "item_id": "gap:67fbdfb989c0",
    "label": "CORRECT",
    "reasons": [
      "evidence intersects reviewed relevant papers"
    ],
    "errors": [],
    "score_components": {
      "field_completeness": 1.0,
      "evidence_support": 1.0,
      "abstract_only": 0.0
    }
  },
  {
    "item_id": "gap:4289ba45e918",
    "label": "CORRECT",
    "reasons": [
      "evidence intersects reviewed relevant papers"
    ],
    "errors": [],
    "score_components": {
      "field_completeness": 1.0,
      "evidence_support": 1.0,
      "abstract_only": 0.0
    }
  },
  {
    "item_id": "gap:8349a335cee2",
    "label": "CORRECT",
    "reasons": [
      "evidence intersects reviewed relevant papers"
    ],
    "errors": [],
    "score_components": {
      "field_completeness": 1.0,
      "evidence_support": 1.0,
      "abstract_only": 0.0
    }
  },
  {
    "item_id": "gap:ffd6afbf94d7",
    "label": "CORRECT",
    "reasons": [
      "evidence intersects reviewed relevant papers"
    ],
    "errors": [],
    "score_components": {
      "field_completeness": 1.0,
      "evidence_support": 1.0,
      "abstract_only": 0.0
    }
  },
  {
    "item_id": "gap:5139d9b60e7a",
    "label": "CORRECT",
    "reasons": [
      "evidence intersects reviewed relevant papers"
    ],
    "errors": [],
    "score_components": {
      "field_completeness": 1.0,
      "evidence_support": 1.0,
      "abstract_only": 0.0
    }
  },
  {
    "item_id": "gap:00f8363cf1fe",
    "label": "CORRECT",
    "reasons": [
      "evidence intersects reviewed relevant papers"
    ],
    "errors": [],
    "score_components": {
      "field_completeness": 1.0,
      "evidence_support": 1.0,
      "abstract_only": 0.0
    }
  },
  {
    "item_id": "mismatch:d19e597ea80a",
    "label": "CORRECT",
    "reasons": [
      "evidence intersects reviewed relevant papers"
    ],
    "errors": [],
    "score_components": {
      "field_completeness": 1.0,
      "evidence_support": 1.0,
      "abstract_only": 0.0
    }
  },
  {
    "item_id": "mismatch:d19e597ea80a",
    "label": "CORRECT",
    "reasons": [
      "evidence intersects reviewed relevant papers"
    ],
    "errors": [],
    "score_components": {
      "field_completeness": 1.0,
      "evidence_support": 1.0,
      "abstract_only": 0.0
    }
  },
  {
    "item_id": "mismatch:2e0e53be1539",
    "label": "CORRECT",
    "reasons": [
      "evidence intersects reviewed relevant papers"
    ],
    "errors": [],
    "score_components": {
      "field_completeness": 1.0,
      "evidence_support": 1.0,
      "abstract_only": 0.0
    }
  },
  {
    "item_id": "mismatch:2e0e53be1539",
    "label": "CORRECT",
    "reasons": [
      "evidence intersects reviewed relevant papers"
    ],
    "errors": [],
    "score_components": {
      "field_completeness": 1.0,
      "evidence_support": 1.0,
      "abstract_only": 0.0
    }
  },
  {
    "item_id": "mismatch:fc5e962ac781",
    "label": "CORRECT",
    "reasons": [
      "evidence intersects reviewed relevant papers"
    ],
    "errors": [],
    "score_components": {
      "field_completeness": 1.0,
      "evidence_support": 1.0,
      "abstract_only": 0.0
    }
  },
  {
    "item_id": "mismatch:fc5e962ac781",
    "label": "CORRECT",
    "reasons": [
      "evidence intersects reviewed relevant papers"
    ],
    "errors": [],
    "score_components": {
      "field_completeness": 1.0,
      "evidence_support": 1.0,
      "abstract_only": 0.0
    }
  },
  {
    "item_id": "mismatch:66a13053800c",
    "label": "CORRECT",
    "reasons": [
      "evidence intersects reviewed relevant papers"
    ],
    "errors": [],
    "score_components": {
      "field_completeness": 1.0,
      "evidence_support": 1.0,
      "abstract_only": 0.0
    }
  },
  {
    "item_id": "mismatch:66a13053800c",
    "label": "CORRECT",
    "reasons": [
      "evidence intersects reviewed relevant papers"
    ],
    "errors": [],
    "score_components": {
      "field_completeness": 1.0,
      "evidence_support": 1.0,
      "abstract_only": 0.0
    }
  },
  {
    "item_id": "mismatch:3013e7371499",
    "label": "UNSUPPORTED",
    "reasons": [],
    "errors": [
      "EVIDENCE_EXTRACTION_UNSUPPORTED"
    ],
    "score_components": {
      "field_completeness": 1.0,
      "evidence_support": 0.0,
      "abstract_only": 0.0
    }
  },
  {
    "item_id": "agg:11cf18b6b031",
    "label": "CORRECT",
    "reasons": [
      "evidence intersects reviewed relevant papers"
    ],
    "errors": [],
    "score_components": {
      "field_completeness": 1.0,
      "evidence_support": 1.0,
      "abstract_only": 0.0
    }
  },
  {
    "item_id": "gap:98bc50ef1537",
    "label": "CORRECT",
    "reasons": [
      "evidence intersects reviewed relevant papers"
    ],
    "errors": [],
    "score_components": {
      "field_completeness": 1.0,
      "evidence_support": 1.0,
      "abstract_only": 0.0
    }
  },
  {
    "item_id": "gap:8ed5db679476",
    "label": "CORRECT",
    "reasons": [
      "evidence intersects reviewed relevant papers"
    ],
    "errors": [],
    "score_components": {
      "field_completeness": 1.0,
      "evidence_support": 1.0,
      "abstract_only": 0.0
    }
  },
  {
    "item_id": "gap:67fbdfb989c0",
    "label": "CORRECT",
    "reasons": [
      "evidence intersects reviewed relevant papers"
    ],
    "errors": [],
    "score_components": {
      "field_completeness": 1.0,
      "evidence_support": 1.0,
      "abstract_only": 0.0
    }
  },
  {
    "item_id": "gap:4289ba45e918",
    "label": "CORRECT",
    "reasons": [
      "evidence intersects reviewed relevant papers"
    ],
    "errors": [],
    "score_components": {
      "field_completeness": 1.0,
      "evidence_support": 1.0,
      "abstract_only": 0.0
    }
  },
  {
    "item_id": "gap:8349a335cee2",
    "label": "CORRECT",
    "reasons": [
      "evidence intersects reviewed relevant papers"
    ],
    "errors": [],
    "score_components": {
      "field_completeness": 1.0,
      "evidence_support": 1.0,
      "abstract_only": 0.0
    }
  },
  {
    "item_id": "gap:ffd6afbf94d7",
    "label": "CORRECT",
    "reasons": [
      "evidence intersects reviewed relevant papers"
    ],
    "errors": [],
    "score_components": {
      "field_completeness": 1.0,
      "evidence_support": 1.0,
      "abstract_only": 0.0
    }
  },
  {
    "item_id": "gap:5139d9b60e7a",
    "label": "CORRECT",
    "reasons": [
      "evidence intersects reviewed relevant papers"
    ],
    "errors": [],
    "score_components": {
      "field_completeness": 1.0,
      "evidence_support": 1.0,
      "abstract_only": 0.0
    }
  },
  {
    "item_id": "gap:00f8363cf1fe",
    "label": "CORRECT",
    "reasons": [
      "evidence intersects reviewed relevant papers"
    ],
    "errors": [],
    "score_components": {
      "field_completeness": 1.0,
      "evidence_support": 1.0,
      "abstract_only": 0.0
    }
  }
]
```

## Coverage-gap audit

```json
[]
```

## Assumption-mismatch audit

```json
[
  {
    "item_id": "mismatch:d19d170e0c66",
    "label": "VALID_CONTRADICTION",
    "reasons": [
      "relation=contradiction",
      "confidence=0.9",
      "evidence_backed=True"
    ],
    "errors": [],
    "score_components": {}
  },
  {
    "item_id": "mismatch:d19e597ea80a",
    "label": "VALID_CONTRADICTION",
    "reasons": [
      "relation=contradiction",
      "confidence=0.85",
      "evidence_backed=True"
    ],
    "errors": [],
    "score_components": {}
  },
  {
    "item_id": "mismatch:d19d170e0c66",
    "label": "VALID_CONTRADICTION",
    "reasons": [
      "relation=contradiction",
      "confidence=0.9",
      "evidence_backed=True"
    ],
    "errors": [],
    "score_components": {}
  },
  {
    "item_id": "mismatch:d19e597ea80a",
    "label": "VALID_CONTRADICTION",
    "reasons": [
      "relation=contradiction",
      "confidence=0.85",
      "evidence_backed=True"
    ],
    "errors": [],
    "score_components": {}
  },
  {
    "item_id": "mismatch:f04a142c21b2",
    "label": "VALID_CONTRADICTION",
    "reasons": [
      "relation=contradiction",
      "confidence=0.9",
      "evidence_backed=True"
    ],
    "errors": [],
    "score_components": {}
  },
  {
    "item_id": "mismatch:2e0e53be1539",
    "label": "VALID_CONTRADICTION",
    "reasons": [
      "relation=contradiction",
      "confidence=0.85",
      "evidence_backed=True"
    ],
    "errors": [],
    "score_components": {}
  },
  {
    "item_id": "mismatch:f04a142c21b2",
    "label": "VALID_CONTRADICTION",
    "reasons": [
      "relation=contradiction",
      "confidence=0.9",
      "evidence_backed=True"
    ],
    "errors": [],
    "score_components": {}
  },
  {
    "item_id": "mismatch:2e0e53be1539",
    "label": "VALID_CONTRADICTION",
    "reasons": [
      "relation=contradiction",
      "confidence=0.85",
      "evidence_backed=True"
    ],
    "errors": [],
    "score_components": {}
  },
  {
    "item_id": "mismatch:7904f504f472",
    "label": "VALID_CONTRADICTION",
    "reasons": [
      "relation=contradiction",
      "confidence=0.9",
      "evidence_backed=True"
    ],
    "errors": [],
    "score_components": {}
  },
  {
    "item_id": "mismatch:fc5e962ac781",
    "label": "VALID_CONTRADICTION",
    "reasons": [
      "relation=contradiction",
      "confidence=0.85",
      "evidence_backed=True"
    ],
    "errors": [],
    "score_components": {}
  },
  {
    "item_id": "mismatch:7904f504f472",
    "label": "VALID_CONTRADICTION",
    "reasons": [
      "relation=contradiction",
      "confidence=0.9",
      "evidence_backed=True"
    ],
    "errors": [],
    "score_components": {}
  },
  {
    "item_id": "mismatch:fc5e962ac781",
    "label": "VALID_CONTRADICTION",
    "reasons": [
      "relation=contradiction",
      "confidence=0.85",
      "evidence_backed=True"
    ],
    "errors": [],
    "score_components": {}
  },
  {
    "item_id": "mismatch:ad7a76edae51",
    "label": "VALID_CONTRADICTION",
    "reasons": [
      "relation=contradiction",
      "confidence=0.9",
      "evidence_backed=True"
    ],
    "errors": [],
    "score_components": {}
  },
  {
    "item_id": "mismatch:66a13053800c",
    "label": "VALID_CONTRADICTION",
    "reasons": [
      "relation=contradiction",
      "confidence=0.85",
      "evidence_backed=True"
    ],
    "errors": [],
    "score_components": {}
  },
  {
    "item_id": "mismatch:ad7a76edae51",
    "label": "VALID_CONTRADICTION",
    "reasons": [
      "relation=contradiction",
      "confidence=0.9",
      "evidence_backed=True"
    ],
    "errors": [],
    "score_components": {}
  },
  {
    "item_id": "mismatch:66a13053800c",
    "label": "VALID_CONTRADICTION",
    "reasons": [
      "relation=contradiction",
      "confidence=0.85",
      "evidence_backed=True"
    ],
    "errors": [],
    "score_components": {}
  },
  {
    "item_id": "mismatch:b6d21023b41b",
    "label": "VALID_CONTRADICTION",
    "reasons": [
      "relation=contradiction",
      "confidence=0.9",
      "evidence_backed=True"
    ],
    "errors": [],
    "score_components": {}
  },
  {
    "item_id": "mismatch:3013e7371499",
    "label": "VALID_CONTRADICTION",
    "reasons": [
      "relation=contradiction",
      "confidence=0.85",
      "evidence_backed=True"
    ],
    "errors": [],
    "score_components": {}
  }
]
```

## Algorithm-binding audit

```json
[
  {
    "item_id": "Random Forest",
    "label": "exact algorithm",
    "reasons": [
      "binding_method=explicit paper mention",
      "confidence=0.98"
    ],
    "errors": [],
    "score_components": {}
  }
]
```

## Known-solution audit

```json
[
  {
    "item_id": "agg:25c1dc1658c1",
    "label": "PARTIALLY_ADDRESSED",
    "reasons": [
      "mitigating_methods=4",
      "local retrieved corpus (7 papers)"
    ],
    "errors": [],
    "score_components": {}
  },
  {
    "item_id": "agg:11cf18b6b031",
    "label": "PARTIALLY_ADDRESSED",
    "reasons": [
      "mitigating_methods=4",
      "local retrieved corpus (7 papers)"
    ],
    "errors": [],
    "score_components": {}
  },
  {
    "item_id": "mismatch:d19d170e0c66",
    "label": "PARTIALLY_ADDRESSED",
    "reasons": [
      "mitigating_methods=4",
      "local retrieved corpus (7 papers)"
    ],
    "errors": [],
    "score_components": {}
  },
  {
    "item_id": "mismatch:d19e597ea80a",
    "label": "PARTIALLY_ADDRESSED",
    "reasons": [
      "mitigating_methods=4",
      "local retrieved corpus (7 papers)"
    ],
    "errors": [],
    "score_components": {}
  },
  {
    "item_id": "mismatch:f04a142c21b2",
    "label": "PARTIALLY_ADDRESSED",
    "reasons": [
      "mitigating_methods=4",
      "local retrieved corpus (7 papers)"
    ],
    "errors": [],
    "score_components": {}
  },
  {
    "item_id": "mismatch:2e0e53be1539",
    "label": "PARTIALLY_ADDRESSED",
    "reasons": [
      "mitigating_methods=4",
      "local retrieved corpus (7 papers)"
    ],
    "errors": [],
    "score_components": {}
  },
  {
    "item_id": "mismatch:7904f504f472",
    "label": "PARTIALLY_ADDRESSED",
    "reasons": [
      "mitigating_methods=4",
      "local retrieved corpus (7 papers)"
    ],
    "errors": [],
    "score_components": {}
  },
  {
    "item_id": "mismatch:fc5e962ac781",
    "label": "PARTIALLY_ADDRESSED",
    "reasons": [
      "mitigating_methods=4",
      "local retrieved corpus (7 papers)"
    ],
    "errors": [],
    "score_components": {}
  },
  {
    "item_id": "mismatch:ad7a76edae51",
    "label": "PARTIALLY_ADDRESSED",
    "reasons": [
      "mitigating_methods=4",
      "local retrieved corpus (7 papers)"
    ],
    "errors": [],
    "score_components": {}
  },
  {
    "item_id": "mismatch:66a13053800c",
    "label": "PARTIALLY_ADDRESSED",
    "reasons": [
      "mitigating_methods=4",
      "local retrieved corpus (7 papers)"
    ],
    "errors": [],
    "score_components": {}
  },
  {
    "item_id": "mismatch:b6d21023b41b",
    "label": "PARTIALLY_ADDRESSED",
    "reasons": [
      "mitigating_methods=4",
      "local retrieved corpus (7 papers)"
    ],
    "errors": [],
    "score_components": {}
  },
  {
    "item_id": "mismatch:3013e7371499",
    "label": "PARTIALLY_ADDRESSED",
    "reasons": [
      "mitigating_methods=4",
      "local retrieved corpus (7 papers)"
    ],
    "errors": [],
    "score_components": {}
  }
]
```

## External-domain search quality

```json
[
  {
    "item_id": "immunology:9f8911d33cf6",
    "label": "GOOD",
    "reasons": [
      "domain=immunology",
      "native_terminology=True"
    ],
    "errors": [],
    "score_components": {}
  },
  {
    "item_id": "immunology:8a70707f3248",
    "label": "GOOD",
    "reasons": [
      "domain=immunology",
      "native_terminology=True"
    ],
    "errors": [],
    "score_components": {}
  },
  {
    "item_id": "immunology:c721f866cdf8",
    "label": "GOOD",
    "reasons": [
      "domain=immunology",
      "native_terminology=True"
    ],
    "errors": [],
    "score_components": {}
  },
  {
    "item_id": "immunology:bc485ab6a0a5",
    "label": "GOOD",
    "reasons": [
      "domain=immunology",
      "native_terminology=True"
    ],
    "errors": [],
    "score_components": {}
  },
  {
    "item_id": "ecology:cf85866e245f",
    "label": "GOOD",
    "reasons": [
      "domain=ecology",
      "native_terminology=True"
    ],
    "errors": [],
    "score_components": {}
  },
  {
    "item_id": "ecology:42cbfb8d1685",
    "label": "GOOD",
    "reasons": [
      "domain=ecology",
      "native_terminology=True"
    ],
    "errors": [],
    "score_components": {}
  },
  {
    "item_id": "ecology:e7a8c2fe6142",
    "label": "GOOD",
    "reasons": [
      "domain=ecology",
      "native_terminology=True"
    ],
    "errors": [],
    "score_components": {}
  },
  {
    "item_id": "ecology:90b7a19580cb",
    "label": "GOOD",
    "reasons": [
      "domain=ecology",
      "native_terminology=True"
    ],
    "errors": [],
    "score_components": {}
  },
  {
    "item_id": "control_theory:edd56532462c",
    "label": "GOOD",
    "reasons": [
      "domain=control_theory",
      "native_terminology=True"
    ],
    "errors": [],
    "score_components": {}
  },
  {
    "item_id": "control_theory:1aeb44aebd6d",
    "label": "GOOD",
    "reasons": [
      "domain=control_theory",
      "native_terminology=True"
    ],
    "errors": [],
    "score_components": {}
  },
  {
    "item_id": "control_theory:cf4dc9e64d17",
    "label": "GOOD",
    "reasons": [
      "domain=control_theory",
      "native_terminology=True"
    ],
    "errors": [],
    "score_components": {}
  },
  {
    "item_id": "control_theory:7bb446443be2",
    "label": "GOOD",
    "reasons": [
      "domain=control_theory",
      "native_terminology=True"
    ],
    "errors": [],
    "score_components": {}
  },
  {
    "item_id": "neuroscience:137802d4a28f",
    "label": "GOOD",
    "reasons": [
      "domain=neuroscience",
      "native_terminology=True"
    ],
    "errors": [],
    "score_components": {}
  },
  {
    "item_id": "neuroscience:fb6bcaefda57",
    "label": "GOOD",
    "reasons": [
      "domain=neuroscience",
      "native_terminology=True"
    ],
    "errors": [],
    "score_components": {}
  },
  {
    "item_id": "neuroscience:6db71b2ed9e7",
    "label": "GOOD",
    "reasons": [
      "domain=neuroscience",
      "native_terminology=True"
    ],
    "errors": [],
    "score_components": {}
  },
  {
    "item_id": "dynamical_systems:63078f59f7b9",
    "label": "GOOD",
    "reasons": [
      "domain=dynamical_systems",
      "native_terminology=True"
    ],
    "errors": [],
    "score_components": {}
  },
  {
    "item_id": "dynamical_systems:b532f92c01eb",
    "label": "GOOD",
    "reasons": [
      "domain=dynamical_systems",
      "native_terminology=True"
    ],
    "errors": [],
    "score_components": {}
  },
  {
    "item_id": "dynamical_systems:9af43699457d",
    "label": "GOOD",
    "reasons": [
      "domain=dynamical_systems",
      "native_terminology=True"
    ],
    "errors": [],
    "score_components": {}
  },
  {
    "item_id": "dynamical_systems:2a09e5779cc7",
    "label": "GOOD",
    "reasons": [
      "domain=dynamical_systems",
      "native_terminology=True"
    ],
    "errors": [],
    "score_components": {}
  }
]
```

## Mechanism quality

```json
[
  {
    "item_id": "immune_memory",
    "label": "VALID_OPERATIONAL_MECHANISM",
    "reasons": [
      "signature_fields=8/8",
      "evidence_supported=True"
    ],
    "errors": [],
    "score_components": {
      "complete_signature": 1.0,
      "evidence_support": 1.0
    }
  },
  {
    "item_id": "observability",
    "label": "VALID_OPERATIONAL_MECHANISM",
    "reasons": [
      "signature_fields=8/8",
      "evidence_supported=True"
    ],
    "errors": [],
    "score_components": {
      "complete_signature": 1.0,
      "evidence_support": 1.0
    }
  },
  {
    "item_id": "homeostasis",
    "label": "VALID_OPERATIONAL_MECHANISM",
    "reasons": [
      "signature_fields=8/8",
      "evidence_supported=True"
    ],
    "errors": [],
    "score_components": {
      "complete_signature": 1.0,
      "evidence_support": 1.0
    }
  }
]
```

## Alignment quality

```json
[
  {
    "item_id": "agg:25c1dc1658c1:immune_memory",
    "label": "PLAUSIBLE_MATCH",
    "reasons": [
      "score=0.6539999999999999",
      "matched_slots=['aggregation']",
      "conflicts=[]"
    ],
    "errors": [],
    "score_components": {}
  },
  {
    "item_id": "agg:25c1dc1658c1:observability",
    "label": "SURFACE_SIMILARITY",
    "reasons": [
      "score=0.15",
      "matched_slots=['aggregation']",
      "conflicts=[]"
    ],
    "errors": [
      "ALIGNMENT_SURFACE_ONLY"
    ],
    "score_components": {}
  },
  {
    "item_id": "agg:25c1dc1658c1:homeostasis",
    "label": "STRONG_STRUCTURAL_MATCH",
    "reasons": [
      "score=0.71",
      "matched_slots=['aggregation']",
      "conflicts=[]"
    ],
    "errors": [],
    "score_components": {}
  }
]
```

## Candidate rubric

```json
[
  {
    "item_id": "cand:fbc58920c6a4",
    "label": "RUBRIC",
    "reasons": [],
    "errors": [],
    "score_components": {
      "problem_specificity": 4.0,
      "evidence_strength": 4.0,
      "algorithm_binding": 4.0,
      "mechanism_operationality": 2.0,
      "modification_specificity": 4.0,
      "information_feasibility": 4.0,
      "novelty_honesty": 2.0,
      "falsifiability": 4.0,
      "experiment_feasibility": 4.0,
      "purpose_value": 4.0
    }
  },
  {
    "item_id": "cand:4b2f1b6cfdc5",
    "label": "RUBRIC",
    "reasons": [],
    "errors": [],
    "score_components": {
      "problem_specificity": 4.0,
      "evidence_strength": 4.0,
      "algorithm_binding": 4.0,
      "mechanism_operationality": 2.0,
      "modification_specificity": 4.0,
      "information_feasibility": 4.0,
      "novelty_honesty": 2.0,
      "falsifiability": 4.0,
      "experiment_feasibility": 4.0,
      "purpose_value": 4.0
    }
  },
  {
    "item_id": "cand:e87a39f7951f",
    "label": "RUBRIC",
    "reasons": [],
    "errors": [],
    "score_components": {
      "problem_specificity": 4.0,
      "evidence_strength": 4.0,
      "algorithm_binding": 4.0,
      "mechanism_operationality": 2.0,
      "modification_specificity": 4.0,
      "information_feasibility": 4.0,
      "novelty_honesty": 2.0,
      "falsifiability": 4.0,
      "experiment_feasibility": 4.0,
      "purpose_value": 4.0
    }
  }
]
```

## Stage funnel

- retrieved_papers: 7
- relevant_papers: 5
- evidence_bearing_papers: 4
- valid_gaps: 34
- gaps_surviving_known_solution_checks: 12
- relevant_external_papers: 2
- valid_mechanisms: 3
- strong_structural_alignments: 1
- candidates_surviving_falsification: 3

## Dominant errors

- EVIDENCE_EXTRACTION_UNSUPPORTED: 2
- ALIGNMENT_SURFACE_ONLY: 1

Dominant bottleneck: **EVIDENCE**

## Targeted repairs made

- Added typed structural-topology compatibility to alignment; justified by operational mechanisms producing surface-only alignments.
- Corrected candidate rubric to recognize aggregation/objective modifications; this repairs measurement, not synthesis.
- Stopped classifying insufficient unreviewed local search as KNOWN_SOLUTION_MISSED without an annotated expected solution.

## Before/after comparison

```json
{
  "alignment_surface_errors": {
    "after": 1,
    "before": 3
  },
  "candidate_vague_errors": {
    "after": 0,
    "before": 3
  },
  "known_solution_missed_errors": {
    "after": 0,
    "before": 0
  },
  "repairs": [
    "Added typed structural-topology compatibility to alignment; justified by operational mechanisms producing surface-only alignments.",
    "Corrected candidate rubric to recognize aggregation/objective modifications; this repairs measurement, not synthesis.",
    "Stopped classifying insufficient unreviewed local search as KNOWN_SOLUTION_MISSED without an annotated expected solution."
  ],
  "retrieval_metrics": {
    "after": {
      "abstract_availability": 1.0,
      "duplicate_rate": 0.0,
      "full_evidence_availability": 1.0,
      "highly_relevant_paper_count": 4,
      "ndcg_at_10": 1.0,
      "ndcg_at_20": 1.0,
      "precision_at_10": 0.5,
      "precision_at_20": 0.25,
      "precision_at_5": 1.0,
      "relevant_paper_count": 5,
      "source_diversity": 2,
      "year_coverage": 4
    },
    "before": {
      "abstract_availability": 1.0,
      "duplicate_rate": 0.0,
      "full_evidence_availability": 1.0,
      "highly_relevant_paper_count": 4,
      "ndcg_at_10": 1.0,
      "ndcg_at_20": 1.0,
      "precision_at_10": 0.5,
      "precision_at_20": 0.25,
      "precision_at_5": 1.0,
      "relevant_paper_count": 5,
      "source_diversity": 2,
      "year_coverage": 4
    },
    "changed": false
  },
  "strong_structural_alignments": {
    "after": 1,
    "before": 0
  }
}
```

## Remaining limitations

- Offline papers and relevance labels are synthetic CI fixtures.
- No whole-literature recall is claimed.
- No real SPECTER2 quality benefit was evaluated.
- Automated audits require human review before scientific use.
