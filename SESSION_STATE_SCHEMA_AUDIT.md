# Session-state schema audit

## Failure and reproduction

The production failure was reproduced by retaining a pre-v2, object-shaped
`DomainSelection` in `current_external_result` and rerunning Part 2. The current
renderer accessed `unmatched_required_roles` directly, so Streamlit hot reload
raised `AttributeError`. The repository source and HEAD were internally
consistent; retained process/session data, rather than a mixed source build,
was sufficient to cause the failure.

## State boundary

`current_external_result` is now the versioned serialization boundary. It stores
an `external-discovery-v2` dictionary, never a live dataclass. Nested domain
selections carry `domain-selection-v2`; the session carries `session-state-v2`.
The centralized resolver accepts current dictionaries, legacy dictionaries,
legacy duck-typed objects, and mixed domain-selection lists.

Resolution statuses are `CURRENT`, `MIGRATED`, `PARTIALLY_MIGRATED`,
`IDENTITY_MISMATCH`, `INVALID_SCHEMA`, `UNRECOVERABLE`, and `ABSENT`.

Legacy-only missing scores are represented as `None`; they are not invented as
zeroes. The UI renders these as “Not recorded in this legacy result.” Malformed
domain items are skipped individually and reported as migration warnings.

## Invalidation policy

Identity mismatch, invalid schema, and unrecoverable external state clear only
external discovery and its derived idea/result state. Purpose, ML corpus,
research run, direction portfolio, selected direction, and selected gap remain
available so the normal Part 2 action can rebuild safely under the existing
search policy and rate limits.

## Audited session values

The audit covered the purpose contract, ML papers/corpus, research run, gap
collections, direction snapshots, selected gap, external result, papers,
mechanisms, alignments, candidate/derivation portfolios, selected idea context,
explanation, audit result, diagnostics, and navigation keys. This repair changes
only the external-result persistence boundary; the other established models and
workflow transitions remain unchanged.
