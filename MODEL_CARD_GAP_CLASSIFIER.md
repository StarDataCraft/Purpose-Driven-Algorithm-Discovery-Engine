# Gap Sentence Classifier Model Card

## Status

No trained classifier checkpoint is committed with this repository. No SciBERT
performance claim is made.

The default classifier is a deterministic, auditable weak-supervision rule
ensemble. Full mode can load a **locally fine-tuned** SciBERT checkpoint supplied
by the operator. The base `allenai/scibert_scivocab_uncased` encoder is never
treated as a ready-made limitation classifier.

## Intended use

Multi-label classification of bounded scientific sentence contexts into
background, contribution, method, result, limitation, failure condition,
assumption, future work, missing evaluation, deployment/resource constraint,
contradictory result, and other.

## Training and evaluation

`python -m training.train_gap_classifier` creates a paper-level split and
training metadata scaffold. A real training run requires optional local
transformer dependencies and must implement the requirements recorded in that
metadata. `python -m training.evaluate_gap_classifier` evaluates the rule
baseline on annotations.

The seed dataset is too small for credible model-performance claims. Any future
checkpoint must report held-out per-label precision, recall, F1, macro/micro F1,
calibration, latency, memory use, and contribution/motivation false positives.

## Deployment readiness gate

Production activation requires paper-level splits with no adjacent-sentence
leakage, at least 50 adjudicated examples for each critical label, macro F1 ≥
0.75, micro F1 ≥ 0.80, critical-label precision ≥ 0.80 and recall ≥ 0.70,
expected calibration error ≤ 0.10, and no regression against the rule baseline
on contribution/motivation false positives. These are project engineering
thresholds, not universal scientific claims. Until this gate passes, SciBERT
output is EXPERIMENTAL and cannot promote a gap.

## Limitations

Weak rules have limited recall on implicit gaps and can conflict. Annotation
coverage is small. Model outputs remain evidence-ranking signals, not proof that
a research gap exists.
