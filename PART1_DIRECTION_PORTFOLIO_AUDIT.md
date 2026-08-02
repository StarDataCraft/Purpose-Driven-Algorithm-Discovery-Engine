# Part 1 direction-portfolio audit

## Pre-repair loss trace

The previous UI passed only `consolidation.promoted` into
`build_direction_portfolio`. Consequently, scientifically coherent families
that narrowly missed promotion were invisible rather than explicitly evaluated
as exploratory alternatives.

Offline baseline funnels were:

| Purpose | Raw gaps | Canonical families | Promoted | Displayed before |
|---|---:|---:|---:|---:|
| Recurring drift and slow recovery | 18 | 9 | 2 | 2 |
| Training–inference missingness shift | 10 | 7 | 1 | 1 |
| Dynamic cluster birth/death | 12 | 8 | 1 | 1 |

Losses were traced to single-paper status, purpose incompatibility, malformed
or unknown algorithm binding, and promoted-only portfolio construction. UNKNOWN
and incompatible families remain rejected.

## Post-repair benchmark

| Purpose | Recommended | Exploratory | Displayed | Duplicate suppression | Diversity represented |
|---|---:|---:|---:|---:|---|
| Recurring drift | 2 | 2 | 4 | 0 in fixture | 2 topologies, 4 components, 3 algorithm families, 2 gap types |
| Missingness shift | 1 | 1 | 2 | 0 in fixture | 2 components, 2 algorithm families, 2 gap types |
| Dynamic clustering | 1 | 2 | 3 | 0 in fixture | 2 lifecycle topologies, 2 components, 2 gap types |

Missingness honestly remains a two-direction portfolio: no third family passes
the bounded exploratory coherence gates. The UI explains this rather than
manufacturing another card.

## Selection policy

Recommended families must retain full promotion status plus complete structured
fields, supporting paper records, a testable metric, and an unresolved
remainder. Exploratory families are restricted to coherent `SINGLE_PAPER`,
borderline-testability, or incomplete-known-solution-search cases and display
their exact limitation.

Selection is deterministic. It ranks quality, then adds a diversity
contribution computed from task, application, failure topology, algorithm
family, affected component, gap type, metric, evidence set, and known-solution
status. Exact structural variants are suppressed. One bounded pass over eligible
exploratory families occurs only when fewer than three recommended directions
exist; it performs no new API requests and does not weaken global gates.
