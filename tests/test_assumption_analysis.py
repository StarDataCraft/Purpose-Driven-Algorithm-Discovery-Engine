from assumption_analysis import (
    AlgorithmAssumption, ObservedCondition, detect_assumption_mismatches,
    load_assumption_registry, mismatch_to_signature,
)


def condition(predicate):
    return ObservedCondition(
        f"c:{predicate}", "p1", predicate, predicate, "present", "application",
        predicate, "limitations", "test", .95,
    )


def test_required_predicate_relations(purpose):
    registry = load_assumption_registry()
    cases = [
        ("Random Forest", "recurring_drift", "contradiction"),
        ("Deep tabular models", "inference_missingness", "contradiction"),
        ("K-means", "dynamic_component_count", "contradiction"),
    ]
    for algorithm, observed, expected in cases:
        matches = detect_assumption_mismatches(
            registry, [condition(observed)], {algorithm}, purpose
        )
        assert matches[0].contradiction_relation == expected
    gaussian = next(a for a in registry if a.normalized_predicate == "gaussianity")
    assert detect_assumption_mismatches(
        [gaussian], [condition("gaussian_data")], {"Gaussian Mixture Model"}, purpose
    ) == []


def test_variant_exception_prevents_false_mismatch(purpose):
    registry = load_assumption_registry()
    matches = detect_assumption_mismatches(
        registry, [condition("recurring_drift")], {"Random Forest"}, purpose,
        variant_names=["Adaptive Random Forest"],
    )
    assert matches == []


def test_mismatch_converts_to_backward_compatible_gap(purpose):
    mismatch = detect_assumption_mismatches(
        load_assumption_registry(), [condition("dynamic_component_count")],
        {"K-means"}, purpose,
    )[0]
    gap = mismatch_to_signature(mismatch, purpose)
    assert gap.gap_type == "structural"
    assert gap.mismatch_id
    assert gap.affected_algorithm == "K-means"
