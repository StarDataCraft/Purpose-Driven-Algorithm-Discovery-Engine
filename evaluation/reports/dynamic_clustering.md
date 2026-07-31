# Quality evaluation: dynamic_clustering

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
  "paper_corpus_fingerprint": "b6995a3c943e146d6da5199b905306115e52afa78a914f50ee42abf20356aafc",
  "pipeline_version": "d6e2355a8c220f808644073dd7c146cbfef9a20f",
  "query_generator_version": "problem-query-v2",
  "random_seed": 47,
  "run_id": "evaluation:dynamic_clustering:synthetic-ci-v1",
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
      "paper_id": "synthetic:dynamic_clustering:1",
      "relevance_label": "HIGHLY_RELEVANT",
      "source": "mock_arxiv",
      "title": "[SYNTHETIC] K-means for cluster birth and death",
      "year": 2022
    },
    {
      "paper_id": "synthetic:dynamic_clustering:3",
      "relevance_label": "HIGHLY_RELEVANT",
      "source": "mock_arxiv",
      "title": "[SYNTHETIC] K-means for heterogeneous density",
      "year": 2024
    },
    {
      "paper_id": "synthetic:dynamic_clustering:0",
      "relevance_label": "HIGHLY_RELEVANT",
      "source": "mock_openalex",
      "title": "[SYNTHETIC] K-means for dynamic clustering",
      "year": 2021
    },
    {
      "paper_id": "synthetic:dynamic_clustering:2",
      "relevance_label": "HIGHLY_RELEVANT",
      "source": "mock_openalex",
      "title": "[SYNTHETIC] K-means for split-merge clustering",
      "year": 2023
    },
    {
      "paper_id": "synthetic:dynamic_clustering:5",
      "relevance_label": "RELEVANT",
      "source": "mock_arxiv",
      "title": "[SYNTHETIC] Study of streaming clustering",
      "year": 2021
    },
    {
      "paper_id": "synthetic:dynamic_clustering:8",
      "relevance_label": "PARTIALLY_RELEVANT",
      "source": "mock_openalex",
      "title": "[SYNTHETIC] Broad streaming clustering survey",
      "year": 2024
    },
    {
      "paper_id": "synthetic:dynamic_clustering:4",
      "relevance_label": "HIGHLY_RELEVANT",
      "source": "mock_openalex",
      "title": "[SYNTHETIC] K-means for changing number of clusters",
      "year": 2025
    },
    {
      "paper_id": "synthetic:dynamic_clustering:10",
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

- `streaming clustering cluster birth death split merge under heterogeneous density` — broad; unique=8; relevant=6; labels=[]
- `streaming clustering manage component lifecycle without fixed K` — broad; unique=8; relevant=6; labels=[]
- `nonstationary heterogeneous-density streams cluster birth death split merge under heterogeneous density` — broad; unique=8; relevant=6; labels=[]
- `streaming clustering failure boundary research` — broad; unique=8; relevant=6; labels=[]
- `streaming clustering cluster recovery delay` — broad; unique=8; relevant=6; labels=[]
- `streaming clustering deployment constraints` — broad; unique=8; relevant=6; labels=[]

## Retrieval metrics

- precision_at_5: 1.0
- precision_at_10: 0.6
- precision_at_20: 0.3
- ndcg_at_10: 0.9882
- ndcg_at_20: 0.9882
- relevant_paper_count: 6
- highly_relevant_paper_count: 5
- source_diversity: 2
- year_coverage: 5
- duplicate_rate: 0.0
- abstract_availability: 1.0
- full_evidence_availability: 1.0

## Top retrieved papers and relevance labels

```json
[
  {
    "paper_id": "synthetic:dynamic_clustering:1",
    "title": "[SYNTHETIC] K-means for cluster birth and death",
    "year": 2022,
    "source": "mock_arxiv",
    "relevance_label": "HIGHLY_RELEVANT"
  },
  {
    "paper_id": "synthetic:dynamic_clustering:3",
    "title": "[SYNTHETIC] K-means for heterogeneous density",
    "year": 2024,
    "source": "mock_arxiv",
    "relevance_label": "HIGHLY_RELEVANT"
  },
  {
    "paper_id": "synthetic:dynamic_clustering:0",
    "title": "[SYNTHETIC] K-means for dynamic clustering",
    "year": 2021,
    "source": "mock_openalex",
    "relevance_label": "HIGHLY_RELEVANT"
  },
  {
    "paper_id": "synthetic:dynamic_clustering:2",
    "title": "[SYNTHETIC] K-means for split-merge clustering",
    "year": 2023,
    "source": "mock_openalex",
    "relevance_label": "HIGHLY_RELEVANT"
  },
  {
    "paper_id": "synthetic:dynamic_clustering:5",
    "title": "[SYNTHETIC] Study of streaming clustering",
    "year": 2021,
    "source": "mock_arxiv",
    "relevance_label": "RELEVANT"
  },
  {
    "paper_id": "synthetic:dynamic_clustering:8",
    "title": "[SYNTHETIC] Broad streaming clustering survey",
    "year": 2024,
    "source": "mock_openalex",
    "relevance_label": "PARTIALLY_RELEVANT"
  },
  {
    "paper_id": "synthetic:dynamic_clustering:4",
    "title": "[SYNTHETIC] K-means for changing number of clusters",
    "year": 2025,
    "source": "mock_openalex",
    "relevance_label": "HIGHLY_RELEVANT"
  },
  {
    "paper_id": "synthetic:dynamic_clustering:10",
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
    "item_id": "mismatch:6ebff295a522",
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
    "item_id": "agg:43d943da0579",
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
    "item_id": "coverage-gap:20be06c14bf7",
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
    "item_id": "mismatch:cc6ce1535c7e",
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
    "item_id": "mismatch:cc6ce1535c7e",
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
    "item_id": "mismatch:6e4cfa342486",
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
    "item_id": "mismatch:6e4cfa342486",
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
    "item_id": "mismatch:d0dc019003a6",
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
    "item_id": "mismatch:d0dc019003a6",
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
    "item_id": "mismatch:1aa2ecdaa358",
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
    "item_id": "mismatch:1aa2ecdaa358",
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
    "item_id": "mismatch:63a5712556db",
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
    "item_id": "mismatch:63a5712556db",
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
    "item_id": "gap:ecc01a4cef0b",
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
    "item_id": "gap:3f456f3194ff",
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
    "item_id": "gap:4fb52e9dbdfb",
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
    "item_id": "gap:d77fa3ce6831",
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
    "item_id": "gap:5b6fa19dc225",
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
    "item_id": "gap:ee79292f6e6d",
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
    "item_id": "gap:3c01aaba3f9b",
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
    "item_id": "gap:9f9bdf310d63",
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
    "item_id": "gap:aa5d849de182",
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
    "item_id": "gap:aeffe468b839",
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
    "item_id": "gap:7141b90c392c",
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
    "item_id": "gap:ecc01a4cef0b",
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
    "item_id": "gap:3f456f3194ff",
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
    "item_id": "gap:4fb52e9dbdfb",
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
    "item_id": "gap:d77fa3ce6831",
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
    "item_id": "gap:5b6fa19dc225",
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
    "item_id": "gap:ee79292f6e6d",
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
    "item_id": "gap:3c01aaba3f9b",
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
    "item_id": "gap:9f9bdf310d63",
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
    "item_id": "gap:aa5d849de182",
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
    "item_id": "gap:aeffe468b839",
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
    "item_id": "gap:7141b90c392c",
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
[
  {
    "item_id": "coverage-gap:20be06c14bf7",
    "label": "PLAUSIBLE",
    "reasons": [
      "cluster_size=8",
      "metadata_completeness=0.625",
      "purpose_relevance=1.0",
      "comparable=True"
    ],
    "errors": [],
    "score_components": {}
  }
]
```

## Assumption-mismatch audit

```json
[
  {
    "item_id": "mismatch:cc6ce1535c7e",
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
    "item_id": "mismatch:cc6ce1535c7e",
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
    "item_id": "mismatch:6e4cfa342486",
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
    "item_id": "mismatch:6e4cfa342486",
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
    "item_id": "mismatch:d0dc019003a6",
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
    "item_id": "mismatch:d0dc019003a6",
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
    "item_id": "mismatch:1aa2ecdaa358",
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
    "item_id": "mismatch:1aa2ecdaa358",
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
    "item_id": "mismatch:63a5712556db",
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
    "item_id": "mismatch:63a5712556db",
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
    "item_id": "mismatch:6ebff295a522",
    "label": "VALID_CONTRADICTION",
    "reasons": [
      "relation=contradiction",
      "confidence=0.95",
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
    "item_id": "K-means",
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
    "item_id": "agg:43d943da0579",
    "label": "INSUFFICIENT_SEARCH",
    "reasons": [
      "mitigating_methods=0",
      "local retrieved corpus (8 papers)"
    ],
    "errors": [],
    "score_components": {}
  },
  {
    "item_id": "coverage-gap:20be06c14bf7",
    "label": "INSUFFICIENT_SEARCH",
    "reasons": [
      "mitigating_methods=0",
      "local retrieved corpus (8 papers)"
    ],
    "errors": [],
    "score_components": {}
  },
  {
    "item_id": "mismatch:cc6ce1535c7e",
    "label": "INSUFFICIENT_SEARCH",
    "reasons": [
      "mitigating_methods=0",
      "local retrieved corpus (8 papers)"
    ],
    "errors": [],
    "score_components": {}
  },
  {
    "item_id": "mismatch:6e4cfa342486",
    "label": "INSUFFICIENT_SEARCH",
    "reasons": [
      "mitigating_methods=0",
      "local retrieved corpus (8 papers)"
    ],
    "errors": [],
    "score_components": {}
  },
  {
    "item_id": "mismatch:d0dc019003a6",
    "label": "INSUFFICIENT_SEARCH",
    "reasons": [
      "mitigating_methods=0",
      "local retrieved corpus (8 papers)"
    ],
    "errors": [],
    "score_components": {}
  },
  {
    "item_id": "mismatch:1aa2ecdaa358",
    "label": "INSUFFICIENT_SEARCH",
    "reasons": [
      "mitigating_methods=0",
      "local retrieved corpus (8 papers)"
    ],
    "errors": [],
    "score_components": {}
  },
  {
    "item_id": "mismatch:63a5712556db",
    "label": "INSUFFICIENT_SEARCH",
    "reasons": [
      "mitigating_methods=0",
      "local retrieved corpus (8 papers)"
    ],
    "errors": [],
    "score_components": {}
  },
  {
    "item_id": "mismatch:6ebff295a522",
    "label": "INSUFFICIENT_SEARCH",
    "reasons": [
      "mitigating_methods=0",
      "local retrieved corpus (8 papers)"
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
    "item_id": "biology:7237c3b4aadd",
    "label": "UNCERTAIN",
    "reasons": [
      "domain=biology",
      "native_terminology=False"
    ],
    "errors": [],
    "score_components": {}
  },
  {
    "item_id": "biology:024b6ea2ec88",
    "label": "UNCERTAIN",
    "reasons": [
      "domain=biology",
      "native_terminology=False"
    ],
    "errors": [],
    "score_components": {}
  },
  {
    "item_id": "biology:c9841cdaa6e7",
    "label": "UNCERTAIN",
    "reasons": [
      "domain=biology",
      "native_terminology=False"
    ],
    "errors": [],
    "score_components": {}
  },
  {
    "item_id": "complex_systems:3968c5c41bba",
    "label": "UNCERTAIN",
    "reasons": [
      "domain=complex_systems",
      "native_terminology=False"
    ],
    "errors": [],
    "score_components": {}
  },
  {
    "item_id": "complex_systems:c81a12571ed4",
    "label": "UNCERTAIN",
    "reasons": [
      "domain=complex_systems",
      "native_terminology=False"
    ],
    "errors": [],
    "score_components": {}
  },
  {
    "item_id": "complex_systems:fb974ee1b3fb",
    "label": "UNCERTAIN",
    "reasons": [
      "domain=complex_systems",
      "native_terminology=False"
    ],
    "errors": [],
    "score_components": {}
  },
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
    "item_id": "mismatch:6ebff295a522:immune_memory",
    "label": "PLAUSIBLE_MATCH",
    "reasons": [
      "score=0.6799999999999999",
      "matched_slots=['component_birth_death']",
      "conflicts=[]"
    ],
    "errors": [],
    "score_components": {}
  },
  {
    "item_id": "mismatch:6ebff295a522:observability",
    "label": "SURFACE_SIMILARITY",
    "reasons": [
      "score=0.12",
      "matched_slots=['component_birth_death']",
      "conflicts=[]"
    ],
    "errors": [
      "ALIGNMENT_SURFACE_ONLY"
    ],
    "score_components": {}
  },
  {
    "item_id": "mismatch:6ebff295a522:homeostasis",
    "label": "SURFACE_SIMILARITY",
    "reasons": [
      "score=0.10499999999999998",
      "matched_slots=['component_birth_death']",
      "conflicts=[]"
    ],
    "errors": [
      "ALIGNMENT_SURFACE_ONLY"
    ],
    "score_components": {}
  }
]
```

## Candidate rubric

```json
[
  {
    "item_id": "cand:75d86729e13e",
    "label": "RUBRIC",
    "reasons": [],
    "errors": [],
    "score_components": {
      "problem_specificity": 4.0,
      "evidence_strength": 1.0,
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
    "item_id": "cand:8e86cac965e5",
    "label": "RUBRIC",
    "reasons": [],
    "errors": [],
    "score_components": {
      "problem_specificity": 4.0,
      "evidence_strength": 1.0,
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
    "item_id": "cand:91bf26229fd1",
    "label": "RUBRIC",
    "reasons": [],
    "errors": [],
    "score_components": {
      "problem_specificity": 4.0,
      "evidence_strength": 1.0,
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

- retrieved_papers: 8
- relevant_papers: 6
- evidence_bearing_papers: 6
- valid_gaps: 34
- gaps_surviving_known_solution_checks: 8
- relevant_external_papers: 2
- valid_mechanisms: 3
- strong_structural_alignments: 0
- candidates_surviving_falsification: 3

## Dominant errors

- ALIGNMENT_SURFACE_ONLY: 2
- EVIDENCE_EXTRACTION_UNSUPPORTED: 1

Dominant bottleneck: **ALIGNMENT**

## Targeted repairs made

- Added typed structural-topology compatibility to alignment; justified by operational mechanisms producing surface-only alignments.
- Corrected candidate rubric to recognize aggregation/objective modifications; this repairs measurement, not synthesis.
- Stopped classifying insufficient unreviewed local search as KNOWN_SOLUTION_MISSED without an annotated expected solution.

## Before/after comparison

```json
{
  "alignment_surface_errors": {
    "after": 2,
    "before": 3
  },
  "candidate_vague_errors": {
    "after": 0,
    "before": 0
  },
  "known_solution_missed_errors": {
    "after": 0,
    "before": 8
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
      "highly_relevant_paper_count": 5,
      "ndcg_at_10": 0.9882,
      "ndcg_at_20": 0.9882,
      "precision_at_10": 0.6,
      "precision_at_20": 0.3,
      "precision_at_5": 1.0,
      "relevant_paper_count": 6,
      "source_diversity": 2,
      "year_coverage": 5
    },
    "before": {
      "abstract_availability": 1.0,
      "duplicate_rate": 0.0,
      "full_evidence_availability": 1.0,
      "highly_relevant_paper_count": 5,
      "ndcg_at_10": 0.9882,
      "ndcg_at_20": 0.9882,
      "precision_at_10": 0.6,
      "precision_at_20": 0.3,
      "precision_at_5": 1.0,
      "relevant_paper_count": 6,
      "source_diversity": 2,
      "year_coverage": 5
    },
    "changed": false
  },
  "strong_structural_alignments": {
    "after": 0,
    "before": 0
  }
}
```

## Remaining limitations

- Offline papers and relevance labels are synthetic CI fixtures.
- No whole-literature recall is claimed.
- No real SPECTER2 quality benefit was evaluated.
- Automated audits require human review before scientific use.
