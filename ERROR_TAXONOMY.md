# Scientific quality error taxonomy

Evaluation results may carry multiple errors.

| Stage | Errors |
|---|---|
| Retrieval | `RETRIEVAL_IRRELEVANT`, `RETRIEVAL_MISSED_REFERENCE`, `RERANKING_FAILURE` |
| Queries | `QUERY_TOO_BROAD`, `QUERY_TOO_NARROW`, `QUERY_ALGORITHM_LOCK` |
| Evidence | `EVIDENCE_EXTRACTION_MISSED`, `EVIDENCE_EXTRACTION_UNSUPPORTED`, `WRONG_FAILURE_TYPE`, `WRONG_METRIC`, `WRONG_TRAINING_INFERENCE_SCOPE` |
| Coverage | `COVERAGE_SAMPLE_ARTIFACT`, `COVERAGE_METADATA_ARTIFACT` |
| Assumptions | `ASSUMPTION_WRONG_VARIANT`, `ASSUMPTION_WRONG_SCOPE` |
| Binding/solutions | `ALGORITHM_BINDING_UNSUPPORTED`, `KNOWN_SOLUTION_MISSED` |
| External search | `EXTERNAL_QUERY_LANGUAGE_LEAKAGE`, `EXTERNAL_DOMAIN_MISMATCH` |
| Mechanisms | `MECHANISM_INVALID`, `MECHANISM_METAPHORICAL` |
| Alignment | `ALIGNMENT_SURFACE_ONLY`, `ALIGNMENT_SLOT_INCOMPATIBLE` |
| Candidates | `CANDIDATE_VAGUE`, `CANDIDATE_DUPLICATE`, `CANDIDATE_INFORMATION_LEAKAGE`, `CANDIDATE_UNFALSIFIABLE` |

Coverage audits additionally label plausible gaps, weak support, metadata or
sample artifacts, logical irrelevance, likely addressed gaps, and uncertainty.
Mismatch audits distinguish valid contradictions/tensions from variant
exceptions, wrong algorithm/scope, weak evidence, mitigation, metaphor, and
uncertainty.

The dominant bottleneck is the most frequent reviewed error family. An
`INSUFFICIENT_SEARCH` status is not automatically a `KNOWN_SOLUTION_MISSED`
error: that error requires a reviewed expected solution. This prevents missing
annotations from masquerading as pipeline failure.
