# Cross-task quality evaluation summary

> Synthetic offline annotations are CI fixtures, not scientific ground truth. No whole-literature recall is claimed.

## recurring_concept_drift

- Precision@10: 0.5 → 0.5 (no retrieval repair)
- Surface-only alignment errors: 3 → 1
- Strong alignments: 0 → 1
- Candidate-vague evaluator errors: 3 → 0
- Dominant bottleneck after repair: EVIDENCE

## missingness_shift

- Precision@10: 0.5 → 0.5 (no retrieval repair)
- Surface-only alignment errors: 3 → 2
- Strong alignments: 0 → 0
- Candidate-vague evaluator errors: 0 → 0
- Dominant bottleneck after repair: ALIGNMENT

## dynamic_clustering

- Precision@10: 0.6 → 0.6 (no retrieval repair)
- Surface-only alignment errors: 3 → 2
- Strong alignments: 0 → 0
- Candidate-vague evaluator errors: 0 → 0
- Dominant bottleneck after repair: ALIGNMENT
