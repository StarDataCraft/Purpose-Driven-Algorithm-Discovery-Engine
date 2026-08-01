# Benchmark-driven quality evaluation

For readability, verify that the visible proposal—not raw JSON—names the problem, current behavior, exact slot, state, trigger, rule, inference inputs, expected result, closest methods, main risk, experiment, and kill criterion.

The stage funnel distinguishes evidence events, raw gap instances, canonical families, and promoted directions. Alignment evaluation covers every promoted representative instead of selecting the first raw gap. Task-specific synthetic external papers are CI fixtures and must never be described as live scientific evidence.

Enhanced mode lazily loads `allenai/specter2_base` with the
`allenai/specter2` retrieval/search adapter while preserving sparse and dense
scores. It is not recommended without reviewed-label Precision@5/10/20 and
nDCG@10/20 results showing benefit (or parity with a documented benefit).
Without reviewed labels its quality status is **UNVALIDATED**.

The evaluation harness measures where the production pipeline loses scientific
quality. Passing software tests, returning papers, or generating candidates is
not treated as evidence of scientific validity.

## Benchmarks

Version `1.0.0` defines:

1. recurring concept drift and slow recovery;
2. training–inference missingness shift;
3. dynamic cluster birth/death under heterogeneous density.

Definitions live in `data/evaluation/benchmark_tasks.json`. Curated reference
files deliberately start empty. Do not add a paper until its title and
identifier have been verified. CI uses clearly marked synthetic papers and
labels; these are not literature references or scientific ground truth.

## Running deterministic evaluation

```bash
python -m evaluation.run_benchmark \
  --task recurring_concept_drift \
  --mode offline \
  --output /tmp/recurring_report.json

python -m evaluation.run_benchmark \
  --task missingness_shift \
  --mode offline \
  --output /tmp/missingness_report.json

python -m evaluation.run_benchmark \
  --task dynamic_clustering \
  --mode offline \
  --output /tmp/clustering_report.json
```

The offline mode invokes the real retrieval orchestration with deterministic
mock adapters, then runs structural discovery, known-solution triage, external
translation, mechanism extraction, alignment, and candidate search.

Live evaluation is intentionally excluded from ordinary CI. A live run must
persist its `ResearchRun`, retain its volatile API results outside Git, and use
human-reviewed relevance annotations. Repeat live runs before reporting
variance; never treat one live result as a stable metric.

## Metrics and interpretation

Retrieval reports Precision@5/10/20, nDCG@10/20, counts, source/year diversity,
abstract/full-evidence availability, and per-query contribution. No
whole-literature recall is claimed. “Observed benchmark recall” is permitted
only when a verified curated reference set exists.

Reranking comparisons use the same corpus. TF-IDF fallback is evaluated.
Fake dense backends are software tests labeled `NON-SCIENTIFIC TEST`; they
cannot establish SPECTER2 benefit.

Audits keep author-stated evidence distinct from system-inferred structural
gaps. Candidate generation retains its ten-component 0–4 rubric; the final
user-visible result separately receives ten independent 0–5 review passes for
problem fit, literature, gap evidence, novelty, mechanism, alignment,
executability, experiment quality, readability, and engineering. Every pass
records evidence, problems, an action, and whether a non-generative method may
help. Any score below 4 makes the result explicitly exploratory.

The benchmark runner also records ten adversarial/counterfactual outcomes.
Tests that cannot be supported by fixture metadata—citation removal,
full-text-only evidence, or live/cache scientific drift—are marked limited or
not applicable rather than treated as passes. Full audit records are included
in JSON/Markdown exports and appended to Research Memory when run in the UI.

## Annotation workflow

Enable **Research Tools → Quality Evaluation** in Streamlit. Review papers,
gaps, coverage findings, mismatches, bindings, queries, mechanisms,
alignments, or candidates. Every review stores run/task/item identity,
reviewer, timestamp, label, uncertainty, notes, component scores, and pipeline
version. Reviews can be exported as JSONL, CSV, or Markdown.

Automated labels are prioritization aids only. Human reviewers should mark
uncertainty, distinguish explicit claims from inferred gaps, and verify
training versus inference scope.

## Repair policy and comparisons

Generate baseline reports before modifying production behavior. Select the
dominant stage from reviewed error counts and repair only that stage. Rerun the
same task/version/corpus and report unchanged metrics as unchanged—never imply
improvement from a refactor or corrected evaluator.

The committed deterministic reports show the current before/after comparison.
Transient live reports, response caches, databases, and private annotations
must not be committed.
