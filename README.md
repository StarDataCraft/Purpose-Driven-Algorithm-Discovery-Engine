# Purpose-Driven Cross-Disciplinary Algorithm Discovery Engine

The primary UI is a self-contained three-part workflow: discover bounded research directions, automatically retrieve external evidence and derive ideas, then read one conclusion-first proposal with explicit state, trigger, rule, deterministic diagrams, and a visible critical review. Technical JSON is secondary.

Every displayed final idea receives a typed ten-perspective `ResultAudit`. A score below 4 remains visible and marks the result exploratory. Audits include adversarial-test status and a concise self-critique, are appended to Research Memory without overwriting earlier pipeline versions, and can be inspected under **Research Tools → Multi-angle result audit**. Synthetic fixtures cannot pass human-evidence or prior-art gates. See [`MULTI_ANGLE_AUDIT_REPORT.md`](MULTI_ANGLE_AUDIT_REPORT.md) and [`SOTA_REVIEW.md`](SOTA_REVIEW.md).

OpenAlex requests use the process-wide client in `openalex_client.py`. An optional key is read only from `OPENALEX_API_KEY` or Streamlit secrets; it is never placed in provenance or UI diagnostics. Without a key, the app uses a conservative anonymous budget. Daily quota exhaustion opens the OpenAlex circuit immediately while arXiv and valid cache results remain usable.

> Calibrated evidence flow: deduplicated candidate papers, automatic relevance,
> human-reviewed relevance, and evidence-bearing papers are distinct. Raw gap
> instances consolidate into canonical families; only evidence-gated promoted
> gaps appear in the main selector.

Deployment startup can be checked from a clean lightweight environment with:

```bash
python scripts/deployment_smoke_test.py
```

The supported cloud/CI Python version is 3.12. Enhanced transformer
dependencies are not required for this check.

## Three-part primary experience

1. **Discover directions / 发现方向** — search papers and select an
   evidence-backed candidate direction.
2. **Analyze the gap / 分析 Gap** — inspect coverage and automatically retrieve
   direction-specific external evidence, extract mechanisms, test structural
   correspondence, and derive candidate ideas.
3. **Explain the idea / 解释新想法** — read the exact algorithm change,
   deterministic diagrams, uncertainty, papers, and falsification experiment.

Architecture-oriented views remain under **Research Tools / 研究工具**. See
[`THREE_PART_WORKFLOW.md`](THREE_PART_WORKFLOW.md).

Part 2 inherits the search policy selected in Part 1. Live runs never silently
fall back to fixtures; cache misses offer an explicit live retry; offline runs
remain labeled demonstrations. Changing direction invalidates its external
evidence, while reselecting the same direction can reuse a matching result.

目的驱动的跨学科算法发现引擎

This project proposes testable machine-learning research directions by starting with a
verified problem and an explicit purpose—not an arbitrary algorithm × discipline pairing.
It uses deterministic NLP, typed signatures, constrained graph search, and transparent
scoring. It does **not** use an LLM, generative API, remote embedding service, or hidden AI
summarizer.

## What it does

The workflow is:

```text
purpose or ML/DL gap
→ recent ML/DL paper search
→ evidence-backed gap signature
→ purpose contract
→ gap-driven external paper search
→ mechanism signature
→ structural alignment
→ algorithm slot + operator
→ stochastic candidate search
→ quality-diversity portfolio
→ novelty and falsification audit
→ minimal experiment
→ research memory
```

OpenAlex and arXiv are queried through their public APIs. Each adapter has bounded results,
timeouts, retry/backoff, rate limiting, source isolation, and deduplication. The included
offline corpus makes the complete pipeline testable when the network is unavailable.

## Purpose-first philosophy

A candidate cannot enter search without a `PurposeContract`, selected evidence-backed
`GapSignature`, evaluation metric, affected algorithm/family, and defined inference-time
information. The engine rejects ML-domain mechanisms from its cross-disciplinary view,
checks that weaknesses belong to the selected algorithm, and runs information-leakage and
slot-compatibility rules before scoring.

## Architecture

- `models.py`: typed records for papers, purpose, gaps, mechanisms, operators, candidates,
  families, scoring, and experiments.
- `paper_fetchers.py`: OpenAlex/arXiv adapters, partial failure handling, cache, provenance,
  and DOI/arXiv/title/fingerprint deduplication.
- `query_generation.py`: gap-oriented ML queries and structure-driven external queries.
- `text_processing.py`, `gap_mining.py`: section-aware explicit extraction, corpus
  aggregation, assumption/failure signatures, and evidence confidence.
- `mechanism_mining.py`, `signatures.py`: process-cue validation, generic-word rejection,
  evidence preservation, and external-domain filtering.
- `algorithm_library.py`, `operator_library.py`: curated algorithm skeletons, owned
  weaknesses, modifiable slots, and compositional formula/update schemas.
- `alignment.py`: typed field correspondences, TF-IDF within allowed field pairs, explicit
  compatibility matrix, contradiction and missing-information penalties.
- `graph_engine.py`, `search_engine.py`: bounded typed graph and seeded stochastic
  small/medium/large search with rejected-path traces.
- `portfolio.py`, `direction_families.py`: grid-style quality-diversity archive and
  structurally related research families.
- `synthesis.py`: structured deltas derived only from the selected gap, mechanism, operator,
  and algorithm slot.
- `novelty.py`, `falsification.py`: canonical fingerprints, lexical search queries,
  structural-neighbor warnings, leakage checks, random-signal tests, and kill criteria.
- `experiment_planner.py`: executable stressor, baseline, ablation, metric, compute, and
  reproducibility plans.
- `research_memory.py`, `trend_analysis.py`: SQLite success/failure memory, immutable
  result-audit history, and bounded metadata trends. Repeated failures receive increasing penalties.
- `evaluation/result_audit.py`: ten independent result gates, adversarial status,
  self-critique, and conservative final decisions.
- `app.py`: thin three-part Streamlit workflow with secondary research tools.

Curated JSON resources live in `data/`; deterministic paper fixtures live in
`data/offline_fixtures/`.

## Gap and mechanism mining

Explicit gaps are detected from limitation and future-work cues. Section weighting gives
limitations, discussion, conclusion, and future-work evidence more weight than abstracts.
Repeated compatible gap signatures are aggregated at corpus level. Algorithm assumptions
come from the registry created from the algorithm catalog.

External queries are generated only after a gap exists and incorporate its failure,
observable signal, required response, component, constraints, and timescale. Mechanism
extraction requires a multi-token process with feedback/state/action cues and source
evidence. Generic terms such as “higher”, “novel”, and “performance” are rejected.

## Structural alignment and synthesis

Only corresponding fields are compared: failure↔original problem, signal↔observed signal,
response↔response rule, constraints↔resources, preservation↔target, timescale↔timescale,
and affected component↔compatible slot. Explicit strong/medium/weak compatibility weights
prevent keyword coincidence from dominating.

Modification operators provide required inputs, produced state, formula schemas, inference
requirements, complexity effects, known equivalents, and failure modes. Formulas are
clearly schematic; the engine never invents unsupported mathematical claims.

## Stochastic search and quality diversity

Search supports:

- small: one gap × one mechanism × one slot × one operator;
- medium: complementary mechanisms with one or two operators;
- large: coherent multi-mechanism transfer with a larger complexity penalty.

Randomness chooses among compatible paths only. Every candidate records the seed, sampled
path, mutation steps, selected nodes, and compatibility checks. A fixed corpus/settings/seed
is reproducible. The portfolio limits repeated algorithm families, disciplines, mechanisms,
and modification cells rather than returning near-duplicates.

## Novelty, falsification, and experiments

Novelty is a triage status, never a claim. The engine produces lexical queries and a
canonical fingerprint across family, slot, state, operator, update, memory/routing logic,
and inference information. Known ML equivalents are shown.

Every candidate is challenged by shuffled-signal, fixed-mechanism, simpler-operator,
matched-compute, and parameter-count-matched baselines. It includes a strongest rejection
reason and explicit kill criterion. Experiment plans contain public/synthetic datasets,
stressors, baselines, required ablations, primary/robustness/stability/calibration metrics,
resource reporting, five seeds, success/failure rules, and an information audit.

## Research memory

SQLite stores typed records, rejected fingerprints, repeated failure counts, and ratings.
Failure categories include mechanism-slot incompatibility, metaphor-only transfer,
inference/future/label leakage, duplication, ablation failure, and resource violations.
JSON, CSV utilities, and Markdown experiment export are included. Runtime databases, caches,
and exports are ignored by Git.

## Local setup

Python 3.11 or newer is recommended.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app.py
```

The first page defaults to the bundled evidence corpus. Clear “Use bundled offline
evidence” to query OpenAlex and arXiv. No secrets are required. An optional polite-pool
OpenAlex email can be set by adapting `Settings.openalex_email`.

## Tests and verification

```bash
pytest -q
python -m compileall -q .
python -c "import app"
streamlit run app.py --server.headless true
```

The suite covers invalid/valid mechanism extraction, false cross-disciplinarity, weakness
ownership, purpose preconditions, leakage, typed alignment, operator compatibility,
fixed-seed reproducibility, offline end-to-end behavior, experiment completeness, and
persistent failure memory.

## Streamlit Community Cloud

1. Push the repository to GitHub after local verification.
2. In Streamlit Community Cloud choose **Create app**.
3. Select this repository, branch `main`, and entry point `app.py`.
4. Use the default Python environment; `requirements.txt` contains all dependencies.
5. Deploy. No secret configuration is required.

The app uses no absolute runtime paths, bounds paper/candidate/graph sizes, isolates API
failures, and defaults to lightweight TF-IDF. Runtime SQLite and caches are excluded.

## Known limitations and roadmap

- Most public API results expose only title/abstract; their gap confidence is deliberately
  lower than full-text limitation evidence.
- Seed mechanisms provide a validated ontology fallback. Newly extracted mechanisms are
  conservative and can miss unfamiliar scientific language.
- Structural similarity is an automated screening aid, not an exhaustive novelty review.
- Formula schemas are implementation blueprints, not proofs.
- Large transfers need manual decomposition and substantially stronger empirical evidence.
- Future work includes licensed full-text adapters, richer non-generative scientific
  encoders as optional plugins, BM25 reranking, and importing executed experiment results.

## Structural gap engine

The radar distinguishes five origins:

- explicit author-stated gaps;
- repeated structurally compatible failures;
- relevance-aware coverage omissions;
- assumption–reality mismatches;
- contradictory evidence under comparable settings.

Coverage records preserve `UNKNOWN` rather than fabricating dimensions. A zero-count cell is
not a gap by itself: neighboring support, purpose relevance, metadata completeness, source
and year spread, technical compatibility, and an executable evaluation are required.
Assumption matching uses typed predicates and variant exceptions. Known-solution triage
generates deterministic mitigation queries and reports whether the retrieved sample is
insufficient or suggests a partial solution.

### Engine modes

```bash
# Deployment-safe default
GAP_ENGINE_MODE=lightweight streamlit run app.py

# Optional local SPECTER2; automatically falls back if unavailable
pip install -r requirements-enhanced.txt
GAP_ENGINE_MODE=enhanced ENABLE_SPECTER2=true streamlit run app.py

# Optional fine-tuned local SciBERT classifier
GAP_ENGINE_MODE=full ENABLE_SPECTER2=true ENABLE_SCIBERT=true \
SCIBERT_CHECKPOINT=/absolute/path/to/local/checkpoint streamlit run app.py
```

Other bounds include `TRANSFORMER_DEVICE`, `TRANSFORMER_BATCH_SIZE`,
`TRANSFORMER_MAX_PAPERS`, `TRANSFORMER_MAX_SENTENCES`, and `MODEL_CACHE_DIR`.
Model content never leaves the machine. No remote inference API is used.

Enhanced retrieval combines TF-IDF and local SPECTER2 ranks through reciprocal-rank fusion.
Research clusters use cosine agglomerative clustering; labels come from TF-IDF terms.
Semantic gap aggregation requires compatible type, component, failure topology, and
algorithm family, preventing embedding-only overmerge.

### Weak supervision, SciBERT, and annotations

The lightweight and enhanced modes use a weighted multi-label rule ensemble with section
evidence and conflict handling. Full mode uses hybrid rules plus SciBERT **only** when a
valid locally fine-tuned checkpoint exists. The pretrained encoder alone is not a gap
classifier. The optional Research Tools panel supports human correction and
JSONL/CSV export.

The curated seed annotations are intentionally small:

```bash
python -m training.evaluate_gap_classifier \
  --data data/annotations/gap_sentences.jsonl --output runtime/rule-report.json

python -m training.train_gap_classifier \
  --train data/annotations/gap_sentences.jsonl \
  --output artifacts/scibert_gap_classifier --seed 42
```

Training splits by paper to avoid adjacent-sentence leakage. No trained weights or claimed
classifier improvement are included. See `MODEL_CARD_GAP_CLASSIFIER.md`.

Streamlit Community Cloud should use lightweight mode and only `requirements.txt`.
`requirements-enhanced.txt` is for local/server installations with enough memory for model
weights. Downloaded models, caches, checkpoints, runtime databases, and annotation exports
are ignored by Git.

## Scientific disclaimer

The system proposes **testable algorithm research directions**. It does not prove that a
candidate is genuinely novel, mathematically correct, superior, or publication-ready.
Novelty and value require a careful literature review, implementation, experiments, and
peer evaluation.

## Literature provenance and search modes

The interactive default is **Live scholarly APIs** with OpenAlex and arXiv
enabled. Every action creates one typed `ResearchRun`; Steps 2–10 read that
record instead of reconstructing provenance from widget values.

- `LIVE`: this run received at least one valid scholarly API result.
- `CACHE`: every paper came from a cache created by a successful live request.
- `MIXED`: current paper-level origins combine live, cache, or authorized fixture data.
- `OFFLINE_FIXTURE`: every paper is a bundled demonstration record.
- `FAILED`: no usable corpus was produced.

Explicit fixture mode is not fallback. Fixture fallback occurs only after all
selected live sources fail and the user enables **Allow offline fallback**.
Fixture runs are labeled **DEMONSTRATION ONLY** and are never written to the
live cache. Cache TTL is 86,400 seconds. **Force fresh live search** bypasses
cache reads while preserving rate limits; a failed refresh does not overwrite
the prior Streamlit run.

The UI separates requested and actual publication ranges and shows per-source
request, raw-result, unique-result, cache-hit, failure, and duration counts.
Each paper retains retrieval origin, timestamp, query/request IDs, cache or
fixture identity, ranking scores, and deduplication provenance history.

ML retrieval uses broad task/failure/recovery queries first. Algorithm-focused
queries are generated only after paper evidence produces a confidence-scored
binding. Recurring-drift goals expand to recovery time, adaptation delay,
post-drift regret, recurrence recognition, forgetting, memory, and stability
metrics.

External search converts a selected gap into a typed cross-domain problem
signature and ranks relevant disciplines. Controlled translation profiles
produce short native queries for immunology, ecology, control theory,
neuroscience, dynamical systems, physics, biology, complex systems, operations
research, and mechanism design. Raw ML metrics are not copied into unrelated
disciplines.

To verify a saved candidate, open Research Memory and inspect its
`research_run_id`, then inspect the matching run’s actual mode, sources,
paper IDs, queries, and stage records.

## Benchmark-driven quality evaluation

The optional **Research Tools → Quality Evaluation** panel evaluates the
production pipeline against three versioned tasks: recurring drift,
training–inference missingness shift, and dynamic cluster lifecycle. It shows
retrieval metrics, query contribution, evidence/gap audits, binding and
known-solution audits, external-query and mechanism quality, typed alignment,
the ten-component candidate rubric, stage funnel, and error distribution.

Deterministic CI evaluation uses conspicuously synthetic papers and labels.
They test measurement behavior, not scientific performance. Curated reference
slots are empty until a reviewer verifies real identifiers. See
`EVALUATION_GUIDE.md`, `ERROR_TAXONOMY.md`, and `evaluation/reports/`.
