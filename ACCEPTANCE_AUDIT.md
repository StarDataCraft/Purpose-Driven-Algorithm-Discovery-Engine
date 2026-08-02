# Acceptance audit

The 2026-07-31 overnight audit adds regression coverage for slot-aware modifications, explicit one-page proposal sections, direct-versus-contextual paper roles, and complete deterministic diagram fallbacks. Final evidence is recorded in `OVERNIGHT_FINAL_REPORT.md`.

The 2026-08-01 extended audit adds daily/transient OpenAlex 429 classification, shared limiting, query budgets, circuit breaking, cache coalescing, credential redaction/scan tests, partial arXiv continuation, two complete direction paths, diagram failure fallback, and three expanded scientific benchmark funnels.

The retrieval-calibration iteration separates paper-count semantics, labels
cache-only provenance explicitly, consolidates raw gaps, blocks weak
task-incompatible focused bindings, stores selected-gap snapshots and alignment
paths, and separates supported evidence, system inference, and unknowns in the
primary result view. SciBERT remains gated and citation evidence optional.

The three-part interface exposes exactly three bilingual primary steps.
Direction cards preserve paper roles and relevance semantics; gap analysis
separates paper evidence from inference; idea records preserve snapshots,
alignment paths, and exact modification slots. Part 3 provides four
deterministic diagrams with fallbacks and keeps raw JSON secondary. Technical
provenance, evidence audits, evaluation, annotation, and memory remain under
Research Tools.

Part 2 invokes reusable external discovery and idea pipelines directly.
LIVE/CACHE/OFFLINE policy is inherited from Part 1, direction identity is
validated before reuse, and cache misses or zero mechanism/alignment results
produce stage-specific recovery information. No silent fixture fallback or
alignment-threshold relaxation was added.

Audited after `pytest`, compilation, import, and Streamlit launch checks.

| Criterion | Status | Concrete evidence |
|---|---|---|
| No LLM | PASS | No generative dependency or API call; deterministic modules and `requirements.txt`; source scan is empty. |
| New repository; old prototype untouched | PASS | All work is under this repository; `git status` shows only new local files. |
| Primary workflow fetches papers | PASS | `app.goal_page`, `paper_fetchers.fetch_papers_cached`; OpenAlex and arXiv adapters. |
| Gaps precede external search | PASS | UI pages 1–4 and `generate_external_queries(gap)` require a selected gap. |
| Every candidate has a purpose | PASS | `search_candidates` rejects a missing contract; `AlgorithmCandidate.purpose_contract_id`. |
| Every candidate has evidence-backed gaps | PASS | `synthesize_candidate` copies gap ID and paper IDs; offline end-to-end test. |
| Structured external mechanisms with evidence | PASS | `MechanismSignature`; `extract_mechanisms`; seed/evidence JSON. |
| ML-domain mechanisms excluded | PASS | `cross_domain_only`, alignment/search hard rejection, test. |
| Weaknesses remain bound | PASS | `weakness_belongs`; Naive Bayes/static-coefficients regression test. |
| Invalid mechanism words rejected | PASS | stoplist, process-cue validation, eight-word regression test. |
| Typed structural fusion | PASS | `FIELD_PAIRS`, compatibility matrix, `align`; no all-fields comparison. |
| Hard rejection before ranking | PASS | `preflight_rejections` executes before synthesis/scoring append. |
| Small, medium, large search | PASS | `_mechanism_groups`, scale penalties, three-scale test. |
| Meaningful stochasticity | PASS | Compatible-path shuffling only; trace records selection and checks. |
| Fixed-seed reproducibility | PASS | local `random.Random(seed)` and reproducibility test. |
| Quality-diverse results | PASS | grid archive caps families/mechanisms and unique family/domain/slot cells. |
| Direction families | PASS | typed `DirectionFamily`, `create_direction_families`, UI page 6. |
| Full origin-to-application chain | PASS | gap evidence, structured mechanism, candidate deltas, trade-offs, falsification, and experiment fields shown across pages 3–9. |
| Precise modification slot/operators | PASS | `affected_component`, compatible operator filtering, synthesis fields. |
| Intended use/improvement/constraints | PASS | purpose-derived candidate and experiment fields. |
| Required inference information | PASS | mechanism/operator requirements plus information audit. |
| Failure modes | PASS | mechanism failure boundary and operator failure tests. |
| Novelty queries and neighbors | PASS | `novelty_queries`, known-equivalent operator patterns. |
| Falsification and kill criterion | PASS | `falsification_tests`, strongest reason, explicit kill criterion. |
| Minimal experiment | PASS | `build_experiment`; required ablation regression test. |
| Rejected-candidate memory | PASS | SQLite `failures`; UI stores rejected paths. |
| Failure knowledge affects search | PASS | occurrence-based `failure_penalty`; persistence/penalty test. |
| Trend analysis | PASS | year growth, spread, source diversity, citations; sidebar radar. |
| Visible score components | PASS | `ScoreCard`, scoring test, candidate UI JSON. |
| Automated tests | PASS | 24 tests across 14 test modules. |
| Full suite | PASS | `24 passed in 1.99s` on final run. |
| Syntax | PASS | `python -m compileall -q .`, exit 0. |
| Imports | PASS | core imports and `import app`, exit 0. |
| Streamlit launch | PASS | server advertised localhost:8765; health endpoint returned `ok`; SIGINT logged `Stopping...`. |
| Complete README | PASS | philosophy, architecture, sources, pipeline, setup, deployment, tests, limitations, roadmap, disclaimer. |
| Correct requirements and ignore rules | PASS | bounded compatible dependencies; runtime DB/cache/export/bytecode ignored. |
| Streamlit Community Cloud deployable | PASS | relative runtime paths, no secrets, bounded requests/search, offline fallback, documented entry point. |

## Deliberate scientific limitations

These do not violate the product boundary but must remain visible:

- Abstract-only public records receive weaker evidence than full-text limitation sections.
- Mechanism extraction is conservative and seed-assisted; it can miss unfamiliar terminology.
- Automated novelty is a triage status, never a genuine novelty claim.
- Schematic operator formulas require implementation and empirical validation.
- Large-system transfers require stronger manual literature review and decomposition.

## Structural gap engine upgrade

| Criterion | Status | Evidence |
|---|---|---|
| Five gap types | PASS | `gap_mining.py`, coverage/mismatch/contradiction modules and radar filters. |
| Coverage records from evidence | PASS | `CoverageRecord`, `extract_coverage_records`; provenance/confidence tests. |
| Sparse configurable cubes | PASS | `sparse_coverage_cube`, `coverage_matrix`; no dense tensor materialization. |
| Zero cell is not automatically a gap | PASS | Purpose/support gates and `test_zero_cell_is_not_automatically_gap`. |
| Persistent relevant omissions | PASS | Neighbor/support/metadata/evaluation scoring and missingness test. |
| Metadata incompleteness exposed | PASS | `UNKNOWN`, field provenance, confidence, unknown-ratio hard rejection and UI. |
| Typed algorithm assumptions | PASS | `AlgorithmAssumption`, curated contextual registry and variant exceptions. |
| Typed observed conditions | PASS | `ObservedCondition`, controlled patterns and section/scope provenance. |
| Predicate mismatch engine | PASS | Explicit relation table; contradiction/compatibility/variant tests. |
| Structural gaps remain `GapSignature` | PASS | Additive backward-compatible fields and conversion tests. |
| Conservative contradiction detection | PASS | Comparable-field gate and negative control test. |
| Known-solution triage | PASS | Deterministic mitigation queries, corpus scope, uncertainty, UI status. |
| Lightweight mode default | PASS | `GAP_ENGINE_MODE`, lazy imports, transformer-free subprocess test. |
| Optional local SPECTER2 | PASS | Lazy CPU backend and optional enhanced requirements; no import-time load. |
| Model-load fallback | PASS | `select_embedding_backend` and failure regression test. |
| Hybrid sparse/dense retrieval | PASS | Auditable RRF ranks/scores and deterministic fake-backend tests. |
| Embedding cache invalidation | PASS | Model/content/preprocessing key and changed-abstract test. |
| Research clustering | PASS | Cosine agglomerative threshold clustering and reproducibility test. |
| Semantic aggregation safeguards | PASS | Embedding threshold plus type/component/failure/family compatibility test. |
| Optional SciBERT | PASS | Valid fine-tuned checkpoint required; base encoder never treated as classifier. |
| Weak-supervision fallback | PASS | Weighted multi-label votes, section evidence, conflicts and tests. |
| Human annotation workflow | PASS | Versioned 13-row seed set and optional Research Tools UI/export. |
| Context-aware classification | PASS | Bounded section/previous/target/next representation and test. |
| Training/evaluation tools | PASS | Optional local SciBERT training uses paper splits, class-weighted multi-label BCE, fixed seeds, early stopping, checkpoints, and per-label/macro/micro metrics; no checkpoint was trained in this task. |
| Classifier performance claims | PASS | None made; model card explicitly prohibits claims without held-out evaluation. |
| Research memory migration | PASS | Schema version 2 adds structural/model records and preserves legacy records in test. |
| Resource bounds/diagnostics | PASS | Paper/sentence/cache/annotation bounds and runtime mode/process/truncation display. |
| Streamlit structural views | PASS | Coverage, mismatch, contradiction, clusters, model provenance and annotation panels. |
| Downstream candidate generation | PASS | Existing fixed-seed and AppTest candidate workflows remain green. |
| Community Cloud deployment | PASS | Lightweight default, core requirements unchanged, enhanced stack separate. |
| Optional audit startup isolation | PASS | Core app has no eager result-audit or benchmark import; typed graceful mode preserves Parts 1–3, while strict CI validates canonical model identity and audit callables. |
| Build identity diagnostics | PASS | Running commit and SHA-256 fingerprints for the app and audit contract sources are visible under Build information. |

No checkpoint was trained in this task because the seed dataset is intentionally too
small for a credible scientific performance claim. The command is implemented for a
future adequately sized adjudicated dataset.

## Retrieval and translation foundation

| Criterion | Status | Evidence |
|---|---|---|
| Live-first default | PASS | Discover directions defaults to Live scholarly APIs; OpenAlex/arXiv enabled. |
| Actual mode from provenance | PASS | `ResearchRun.finalize_from_papers`; mocked LIVE/CACHE/FAILED/FIXTURE tests. |
| Explicit fixture versus fallback | PASS | `retrieve_corpus` requires explicit mode or authorized fallback and records reason. |
| Paper-level provenance | PASS | Retrieval origin/time, query/request/cache/fixture/rank fields plus merged history. |
| Complete source counts | PASS | `SourceRetrievalResult` and UI table include raw/unique/cache/failure/duration. |
| Requested/actual year ranges | PASS | Separate `ResearchRun` fields and technical provenance display. |
| Two-stage queries | PASS | `generate_problem_queries`, binding detection, focused queries, production integration. |
| No unsupported AdaBoost binding | PASS | Evidence or explicit family restriction required; query regression test. |
| Recovery metric expansion | PASS | Controlled recurring-drift metric family and tests. |
| Query quality controls | PASS | Length, malformed phrase, unsupported algorithm, information and duplicate gates. |
| Native external translation | PASS | Ten deterministic profiles; recurring-drift translation tests. |
| Relevant domain selection | PASS | Direction-specific role, topology, mechanism-value, query-specificity, and analogy-risk scoring selects three domains by default. |
| Shared run identity | PASS | External stage and candidates retain the originating `run_id`. |
| Research-memory provenance | PASS | Runs and papers persist alongside scientific records and candidates. |
| No generative LLM | PASS | Controlled vocabularies, rules, TF-IDF and optional local encoders only. |

## Benchmark quality evaluation

| Criterion | Status | Evidence |
|---|---|---|
| Three versioned tasks | PASS | `data/evaluation/benchmark_tasks.json`, definition tests. |
| Manual curation without fabricated references | PASS | Empty JSONL curation slots and optional Streamlit review workflow. |
| Retrieval metrics | PASS | Precision@K, nDCG, counts, availability, source/year diversity tests. |
| Query contribution | PASS | Stage/query contribution records with yield and duplicate accounting. |
| Gap/coverage/mismatch audits | PASS | Conservative labels, metadata/sample gates, scope and variant categories. |
| Binding and known-solution audit | PASS | Granularity labels; insufficient unreviewed search is not falsely called a miss. |
| External/mechanism/alignment audits | PASS | Native-language, complete-signature, slot/topology and information checks. |
| Candidate rubric | PASS | Ten independent 0–4 components; exact slot and kill-criterion checks. |
| Error taxonomy and funnel | PASS | Canonical multi-error vocabulary and counts/conversion rates. |
| Reproducible reports | PASS | Run/commit/task/profile/corpus/seed/model/threshold/annotation metadata. |
| Evidence-based repair | PASS | Baseline preceded controlled topology alignment repair; retrieval was unchanged. |
| Human review and persistence | PASS | Optional UI, Research Memory, JSONL/CSV/Markdown exports. |
| Offline CI/live separation | PASS | Mock adapters in CI; live mode requires reviewed annotations and is not automatic. |
| No quality overclaim | PASS | Reports and UI warn that synthetic/automated labels are not ground truth. |
## Part 2 → Part 3 state-transition acceptance

- Candidate and derivation are hard-gated, ranked, and committed atomically.
- Candidate evaluation is internal; there is no candidate selector. The one
  Continue button only navigates to the already committed primary idea.
- Part 3 renders from versioned immutable snapshots and survives cleared
  candidate and derivation portfolios.
- Ordinary reruns and backward navigation preserve the selected idea.
- A direction or gap change invalidates the old selection; same-direction reuse
  preserves it.
- The deployment smoke test verifies automatic context creation in Part 2 and
  then opens that same primary idea in Part 3 without candidate interaction.
- Optional audit or persistence failure cannot erase the core explanation.
