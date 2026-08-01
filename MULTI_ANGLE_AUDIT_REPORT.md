# Multi-angle benchmark audit

Audit date: 2026-08-01. All three corpora are deterministic synthetic CI fixtures. The results below validate audit behavior and expose weaknesses; they do not establish live scientific quality.

| Benchmark task | Original result | Main defect | Detecting dimension | Repair implemented | SOTA method considered | Method tested | Benchmark before | Benchmark after | Added resource cost | Decision | Remaining limitation |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Recurring concept drift / slow recovery | 3 promoted directions, 3 mechanisms, 1 final audited idea | No human-reviewed direct evidence; novelty search insufficient | Evidence/gap validity; known-solution/novelty | Ten-pass audit, adversarial record, visible critical review, exploratory gate | SPECTER2; MultiVerS | Deterministic audit only | Candidate was displayed without a canonical final-result gate | 5/3/3/2/5/5/5/5/4/4; exploratory | No model download; deterministic milliseconds only | Audit architecture adopted; model deferred | Synthetic top-10 P=0.50; no live prior-art recall |
| Training–inference missingness shift | 2 directions, 2 mechanisms, 1 final audited idea | Same evidence/novelty blockers; family-level claim remains broad | Evidence/gap validity; novelty; algorithm specificity | Same audit plus algorithm-family counterfactual | SPECTER2; SciNCL | Deterministic audit only | Candidate passed structural generation | 5/3/3/2/5/5/4/5/4/4; exploratory | No model download | Audit adopted; embedding deferred | Synthetic top-10 P=0.50; abstract-only robustness untestable |
| Dynamic cluster birth/death | 3 directions, 3 mechanisms, 1 final audited idea | Prior-art search insufficient despite a strong structural path | Evidence/gap validity; known-solution/novelty | Same audit plus mechanism substitution and seed checks | SPECTER2; MultiVerS | Deterministic audit only | Candidate passed structural generation | 5/3/3/2/5/5/4/5/4/4; exploratory | No model download | Audit adopted; model deferred | Synthetic top-10 P=0.60; no human review/live-cache comparison |

Score order is user fit, literature, evidence/gap, novelty, mechanism, alignment, specificity, experiment, readability, engineering.

## Counterfactual findings

- Removing the external mechanism removes the valid synthesis input, so the cross-domain contribution is not merely cosmetic in the audited path.
- Alternate mechanisms score below the selected 0.710 alignment in all three fixtures (best alternatives: recurring 0.654, missingness 0.157, clustering 0.630). This is encouraging but not a reviewed false-positive estimate.
- Reversing paper order preserves promoted-direction counts on all three tasks.
- Removing the top-ranked synthetic paper leaves promoted directions, but the fixture has no citation counts; highly-cited-paper robustness remains untested.
- Seed 47 versus 48 retains a candidate on all tasks; portfolio identity/quality still requires a larger stochastic study.
- Abstract-removal and live-versus-cache scientific comparisons cannot be established from these fixtures and remain explicitly limited.

## Cross-task diversity

The tasks do not collapse to one algorithm family or slot: recurring drift binds an ensemble aggregation/recovery path, missingness binds a missingness-aware tree-ensemble information/routing path, and dynamic clustering binds a clustering lifecycle/model-selection path. External evidence remains less diverse than desired because the compact fixture corpus contains a small set of mechanisms. Diversity is recorded, not rewarded independently of evidence.

## Final decision

The audit infrastructure passes its deterministic acceptance purpose. Every current benchmark candidate is **EXPLORATORY**, because human-reviewed evidence and a sufficient known-solution search are absent. No score was raised to force a pass, and no state-of-the-art model adoption is claimed.
