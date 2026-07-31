# Acceptance audit

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
