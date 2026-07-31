# Quality evaluation: missingness_shift

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
  "paper_corpus_fingerprint": "052e692b80e82560d578a3c42b9d75ce497a1212a9acc79b205a93028f212217",
  "pipeline_version": "d6e2355a8c220f808644073dd7c146cbfef9a20f",
  "query_generator_version": "problem-query-v2",
  "random_seed": 47,
  "run_id": "evaluation:missingness_shift:synthetic-ci-v1",
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
      "paper_id": "synthetic:missingness_shift:0",
      "relevance_label": "HIGHLY_RELEVANT",
      "source": "mock_openalex",
      "title": "[SYNTHETIC] tree ensemble for missingness shift",
      "year": 2021
    },
    {
      "paper_id": "synthetic:missingness_shift:5",
      "relevance_label": "RELEVANT",
      "source": "mock_arxiv",
      "title": "[SYNTHETIC] Study of tabular classification",
      "year": 2021
    },
    {
      "paper_id": "synthetic:missingness_shift:8",
      "relevance_label": "PARTIALLY_RELEVANT",
      "source": "mock_openalex",
      "title": "[SYNTHETIC] Broad tabular classification survey",
      "year": 2024
    },
    {
      "paper_id": "synthetic:missingness_shift:1",
      "relevance_label": "HIGHLY_RELEVANT",
      "source": "mock_arxiv",
      "title": "[SYNTHETIC] tree ensemble for train-test missingness mismatch",
      "year": 2022
    },
    {
      "paper_id": "synthetic:missingness_shift:2",
      "relevance_label": "HIGHLY_RELEVANT",
      "source": "mock_openalex",
      "title": "[SYNTHETIC] tree ensemble for MNAR",
      "year": 2023
    },
    {
      "paper_id": "synthetic:missingness_shift:3",
      "relevance_label": "HIGHLY_RELEVANT",
      "source": "mock_arxiv",
      "title": "[SYNTHETIC] tree ensemble for inference-time missing features",
      "year": 2024
    },
    {
      "paper_id": "synthetic:missingness_shift:10",
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

- `tabular classification training inference missingness shift` — broad; unique=7; relevant=5; labels=[]
- `tabular classification remain calibrated when feature availability changes` — broad; unique=7; relevant=5; labels=[]
- `partially observed tabular data training inference missingness shift` — broad; unique=7; relevant=5; labels=[]
- `tabular classification failure boundary research` — broad; unique=7; relevant=5; labels=[]
- `tabular classification worst-case AUROC` — broad; unique=7; relevant=5; labels=[]
- `tabular classification deployment constraints` — broad; unique=7; relevant=5; labels=[]

## Retrieval metrics

- precision_at_5: 0.8
- precision_at_10: 0.5
- precision_at_20: 0.25
- ndcg_at_10: 0.9054
- ndcg_at_20: 0.9054
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
    "paper_id": "synthetic:missingness_shift:0",
    "title": "[SYNTHETIC] tree ensemble for missingness shift",
    "year": 2021,
    "source": "mock_openalex",
    "relevance_label": "HIGHLY_RELEVANT"
  },
  {
    "paper_id": "synthetic:missingness_shift:5",
    "title": "[SYNTHETIC] Study of tabular classification",
    "year": 2021,
    "source": "mock_arxiv",
    "relevance_label": "RELEVANT"
  },
  {
    "paper_id": "synthetic:missingness_shift:8",
    "title": "[SYNTHETIC] Broad tabular classification survey",
    "year": 2024,
    "source": "mock_openalex",
    "relevance_label": "PARTIALLY_RELEVANT"
  },
  {
    "paper_id": "synthetic:missingness_shift:1",
    "title": "[SYNTHETIC] tree ensemble for train-test missingness mismatch",
    "year": 2022,
    "source": "mock_arxiv",
    "relevance_label": "HIGHLY_RELEVANT"
  },
  {
    "paper_id": "synthetic:missingness_shift:2",
    "title": "[SYNTHETIC] tree ensemble for MNAR",
    "year": 2023,
    "source": "mock_openalex",
    "relevance_label": "HIGHLY_RELEVANT"
  },
  {
    "paper_id": "synthetic:missingness_shift:3",
    "title": "[SYNTHETIC] tree ensemble for inference-time missing features",
    "year": 2024,
    "source": "mock_arxiv",
    "relevance_label": "HIGHLY_RELEVANT"
  },
  {
    "paper_id": "synthetic:missingness_shift:10",
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
    "item_id": "agg:17b1dfe234b3",
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
    "item_id": "gap:efe6bca2d05f",
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
    "item_id": "gap:f9075e000cc1",
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
    "item_id": "gap:2311718618ce",
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
    "item_id": "gap:ecad5d735a46",
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
    "item_id": "gap:a72947fc3397",
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
    "item_id": "gap:7d67be0ae559",
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
    "item_id": "gap:d92025a58549",
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
    "item_id": "gap:80058dd0377d",
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
    "item_id": "agg:ec403c0715e8",
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
    "item_id": "gap:efe6bca2d05f",
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
    "item_id": "gap:f9075e000cc1",
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
    "item_id": "gap:2311718618ce",
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
    "item_id": "gap:ecad5d735a46",
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
    "item_id": "gap:a72947fc3397",
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
    "item_id": "gap:7d67be0ae559",
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
    "item_id": "gap:d92025a58549",
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
    "item_id": "gap:80058dd0377d",
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
[]
```

## Algorithm-binding audit

```json
[]
```

## Known-solution audit

```json
[
  {
    "item_id": "agg:17b1dfe234b3",
    "label": "INSUFFICIENT_SEARCH",
    "reasons": [
      "mitigating_methods=0",
      "local retrieved corpus (7 papers)"
    ],
    "errors": [],
    "score_components": {}
  },
  {
    "item_id": "agg:ec403c0715e8",
    "label": "INSUFFICIENT_SEARCH",
    "reasons": [
      "mitigating_methods=0",
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
    "item_id": "agg:17b1dfe234b3:immune_memory",
    "label": "SURFACE_SIMILARITY",
    "reasons": [
      "score=0.15",
      "matched_slots=['update_rule']",
      "conflicts=[]"
    ],
    "errors": [
      "ALIGNMENT_SURFACE_ONLY"
    ],
    "score_components": {}
  },
  {
    "item_id": "agg:17b1dfe234b3:observability",
    "label": "PLAUSIBLE_MATCH",
    "reasons": [
      "score=0.6299999999999999",
      "matched_slots=['update_rule']",
      "conflicts=[]"
    ],
    "errors": [],
    "score_components": {}
  },
  {
    "item_id": "agg:17b1dfe234b3:homeostasis",
    "label": "SURFACE_SIMILARITY",
    "reasons": [
      "score=0.23500000000000001",
      "matched_slots=['update_rule']",
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
[]
```

## Stage funnel

- retrieved_papers: 7
- relevant_papers: 5
- evidence_bearing_papers: 4
- valid_gaps: 18
- gaps_surviving_known_solution_checks: 2
- relevant_external_papers: 2
- valid_mechanisms: 3
- strong_structural_alignments: 0
- candidates_surviving_falsification: 0

## Dominant errors

- ALIGNMENT_SURFACE_ONLY: 2

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
    "before": 2
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
      "ndcg_at_10": 0.9054,
      "ndcg_at_20": 0.9054,
      "precision_at_10": 0.5,
      "precision_at_20": 0.25,
      "precision_at_5": 0.8,
      "relevant_paper_count": 5,
      "source_diversity": 2,
      "year_coverage": 4
    },
    "before": {
      "abstract_availability": 1.0,
      "duplicate_rate": 0.0,
      "full_evidence_availability": 1.0,
      "highly_relevant_paper_count": 4,
      "ndcg_at_10": 0.9054,
      "ndcg_at_20": 0.9054,
      "precision_at_10": 0.5,
      "precision_at_20": 0.25,
      "precision_at_5": 0.8,
      "relevant_paper_count": 5,
      "source_diversity": 2,
      "year_coverage": 4
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
