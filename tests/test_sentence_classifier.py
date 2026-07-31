from annotation_schema import SentenceAnnotation, context_window
from sentence_classifier import (
    HybridGapSentenceClassifier, SciBertGapSentenceClassifier,
)


def annotation():
    return SentenceAnnotation(
        "s", "p", "discussion", "Accuracy is competitive.",
        "The method requires complete features at inference time.",
        "Sensors may fail.", [], "test", "1", "unreviewed",
    )


def test_context_window_preserves_target_and_markers():
    text = context_window(annotation(), 500)
    assert "[SECTION] discussion" in text
    assert "[TARGET] The method requires complete features" in text


def test_hybrid_falls_back_without_checkpoint():
    classifier = HybridGapSentenceClassifier(
        SciBertGapSentenceClassifier("/path/that/does/not/exist")
    )
    result = classifier.classify(annotation())
    assert result.fallback_used
    assert result.active_backend == "weak-supervision+rules"
    assert {"ASSUMPTION", "DEPLOYMENT_CONSTRAINT"} <= set(result.labels)
