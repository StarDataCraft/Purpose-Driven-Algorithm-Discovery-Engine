"""Rule, optional checkpoint-gated SciBERT, and hybrid classifiers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from annotation_schema import SentenceAnnotation, context_window
from weak_supervision import WeakLabelResult, label_sentence


@dataclass
class SentenceClassification:
    labels: list[str]
    probability_by_label: dict[str, float]
    rule_votes: list[dict[str, object]]
    weak_label_confidence: float
    model_version: str
    active_backend: str
    fallback_used: bool
    uncertainty: float
    evidence_quality: float


class RuleGapSentenceClassifier:
    def classify(self, annotation: SentenceAnnotation) -> SentenceClassification:
        result = label_sentence(annotation.target_sentence, annotation.section)
        return SentenceClassification(
            result.labels, result.probability_by_label,
            [vote.__dict__ for vote in result.rule_votes], result.confidence,
            "weak-rules-v1", "rules", False, round(1-result.confidence, 3),
            .9 if annotation.section.casefold() in {"limitations", "discussion"} else .65,
        )


class SciBertGapSentenceClassifier:
    """A fine-tuned local checkpoint is mandatory; base SciBERT is not a classifier."""

    def __init__(self, checkpoint: str, device: str = "cpu"):
        self.checkpoint, self.device = checkpoint, device
        self._pipeline = None

    def _load(self) -> None:
        if not self.checkpoint or not Path(self.checkpoint).exists():
            raise RuntimeError("No valid fine-tuned SciBERT gap-classifier checkpoint")
        if self._pipeline is None:
            from transformers import pipeline
            self._pipeline = pipeline(
                "text-classification", model=self.checkpoint, tokenizer=self.checkpoint,
                device=-1, top_k=None,
            )

    def classify(self, annotation: SentenceAnnotation) -> SentenceClassification:
        self._load()
        raw = self._pipeline(context_window(annotation))[0]
        probabilities = {item["label"]: float(item["score"]) for item in raw}
        labels = [label for label, score in probabilities.items() if score >= .5]
        confidence = max(probabilities.values(), default=0.0)
        return SentenceClassification(
            labels, probabilities, [], confidence, self.checkpoint,
            "scibert-finetuned", False, 1-confidence, .75,
        )


class HybridGapSentenceClassifier:
    def __init__(self, model: SciBertGapSentenceClassifier | None = None):
        self.rules, self.model = RuleGapSentenceClassifier(), model

    def classify(self, annotation: SentenceAnnotation) -> SentenceClassification:
        rule = self.rules.classify(annotation)
        if not self.model:
            rule.fallback_used = True
            rule.active_backend = "weak-supervision+rules"
            return rule
        try:
            model = self.model.classify(annotation)
        except RuntimeError:
            rule.fallback_used = True
            rule.active_backend = "weak-supervision+rules"
            return rule
        probabilities = dict(model.probability_by_label)
        for label, score in rule.probability_by_label.items():
            probabilities[label] = max(score, probabilities.get(label, 0.0))
        labels = sorted(label for label, score in probabilities.items() if score >= .5)
        return SentenceClassification(
            labels, probabilities, rule.rule_votes, rule.weak_label_confidence,
            model.model_version, "hybrid-scibert+rules", False,
            min(rule.uncertainty, model.uncertainty),
            max(rule.evidence_quality, model.evidence_quality),
        )
