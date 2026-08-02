# Upstream direction-generation audit

## Reproduced bottleneck

Production reported one promoted and eight exploratory canonical families. The
portfolio correctly rejected the eight because they were malformed or unbound;
the loss occurred before portfolio selection.

The deterministic recurring-drift fixture trace contained 18 raw gaps and 9
canonical families. Extraction origins were 6 explicit limitation records, 1
repeated aggregation, and 2 assumption mismatches. The production-shaped
`one_direction_diagnostic.json` fixture reproduces 1 promoted plus 8 rejected
families across explicit, contradiction, coverage, assumption/purpose, duplicate,
and wrong-task paths.

Root causes:

- explicit extraction wrote `Unspecified/unspecified` when no algorithm-library
  name appeared in the sentence;
- coverage conversion always wrote an unspecified family;
- contradiction conversion inherited an empty family when comparison metadata
  did not bind a method;
- raw extracted fragments were used as titles even when complete structured
  fields existed;
- the old expansion pass merely rechecked these records.

## Repair architecture

`direction_generation.py` now separates research-direction formation from gap
families. It creates bounded purpose-derived axes, but axes remain hypotheses.
Only candidates with a connected
paper → evidence sentence → gap → family/method class → metric → direction path
are eligible.

Binding is hierarchical: exact algorithm, algorithm family, broad method class,
then UNBOUND. Registry candidates are never evidence. Task-incompatible named
algorithms are rejected, and one deterministic repair pass is allowed for each
unbound record.

Titles and complete problem statements are deterministically regenerated only
when the underlying task, failure, component, metric, and response are present.
Paper compatibility requires hard task and failure/algorithm overlap before
textual relevance can contribute. Purpose-contract sections never create direct
evidence paths.

When fewer than three distinct validated axes exist, the app records shortage
classes and selects at most two missing high-priority axes. Each receives one
query and one source, cache first, with at most four papers per query and eight
total per axis run. The existing rate limiter, cache, circuit breaker, and source
budget remain authoritative. The cycle runs once and then re-extracts,
reconsolidates, and rebuilds.

## Reviewed binding baseline

Nine reviewed records cover recurring drift, missingness shift, and dynamic
clustering. Results: 8/9 exact-family labels, 9/9 when an approved broader method
class is accepted, 3/3 negative examples retained as UNBOUND, and zero known
incompatible-family bindings. This deterministic baseline did not justify adding
a scientific embedding or cross-encoder; those remain evaluation options only.

## Three-purpose offline benchmark

### Recurring concept drift

- 7 axes, 14 generated axis queries, 9 papers, 18 raw gaps.
- 2 titles repaired, 2 family bindings repaired, 5 connected paths.
- Portfolio: 0 recommended, 3 exploratory; 2 topologies and 2 components.
- Titles:
  - Reducing recovery time from slow recovery under drift through aggregation.
  - Reducing recovery time from recurring concept drift through update rule.
  - Reducing recovery time from regime change through update rule.

### Training–inference missingness shift

- 5 axes, 10 generated axis queries, 9 papers, 10 raw gaps.
- 2 titles repaired, 1 family binding repaired, 4 connected paths.
- Portfolio: 1 recommended, 0 exploratory. The bounded expansion diagnoses two
  missing axes, finds no new fixture papers, and honestly retains one direction.
- Title: Reducing missing-feature degradation from missingness shift through routing.

### Dynamic cluster birth/death

- 5 axes, 10 generated axis queries, 9 papers, 12 raw gaps.
- 2 titles repaired, no forced bindings, 2 connected paths.
- Portfolio: 0 recommended, 2 exploratory across two lifecycle topologies.
- Titles:
  - Reducing cluster birth detection delay from stale or redundant centroids through component birth death.
  - Reducing cluster birth detection delay from dynamic cluster birth/death under heterogeneous density through assignment.

Fixture-mode expansion deliberately adds zero papers. Live/cache mode uses the
bounded axis retrieval cycle; it never silently switches fixtures.
