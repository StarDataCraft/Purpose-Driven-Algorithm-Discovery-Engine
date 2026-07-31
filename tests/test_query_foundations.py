from models import Paper
from query_generation import (
    RECOVERY_METRICS, detect_algorithm_bindings, expand_metric_families,
    generate_external_queries, generate_focused_algorithm_queries,
    generate_ml_queries, generate_problem_queries,
    normalize_cross_domain_problem, select_external_domains, validate_queries,
)


def test_recurring_drift_problem_queries_are_broad_and_recovery_oriented(purpose):
    queries, audit = generate_problem_queries(purpose)
    joined = " ".join(queries).casefold()
    assert "recurring concept drift" in joined
    assert "post-drift recovery" in joined
    assert "concept history reuse" in joined
    assert all(len(query) <= 110 for query in queries)
    assert audit.accepted_count == len(queries)
    assert "adaboost" not in joined


def test_algorithm_focus_requires_paper_evidence(purpose):
    bindings = detect_algorithm_bindings([
        Paper("1", "Adaptive random forest under drift",
              "Random forest recovery for recurring concept drift", 2025, "openalex")
    ], purpose)
    queries, _ = generate_focused_algorithm_queries(purpose, bindings)
    assert any("random forest" in query.casefold() for query in queries)
    assert all("adaboost" not in query.casefold() for query in queries)


def test_metric_expansion_preserves_user_metric_and_adds_recovery(purpose):
    metrics = expand_metric_families(purpose)
    assert purpose.primary_metric in metrics
    assert set(["recovery time", "adaptation delay", "post-drift regret"]) <= set(metrics)


def test_validation_rejects_malformed_and_collapses_duplicates():
    accepted, audit = validate_queries([
        "physics remove stationary distribution",
        "immune memory recurrent exposure",
        "immune memory recurrent exposure",
    ])
    assert accepted == ["immune memory recurrent exposure"]
    assert audit.rejection_reasons["contradictory or malformed phrase"] == 1
    assert audit.deduplicated_count == 1


def test_domain_native_queries_exclude_ml_metrics(ml_papers, purpose):
    from gap_mining import mine_gaps

    gap = next(
        item for item in mine_gaps(ml_papers, purpose)
        if "recurring" in item.failure_type
    )
    queries = generate_external_queries(gap)
    forbidden = {"online accuracy", "stationary distribution"}
    for domain in ("biology", "ecology", "immunology", "neuroscience", "physics"):
        joined = " ".join(queries.get(domain, [])).casefold()
        assert not any(term in joined for term in forbidden)
    assert "immune memory" in " ".join(queries["immunology"]).casefold()
    assert "ecological memory" in " ".join(queries["ecology"]).casefold()
    assert "switching" in " ".join(queries["control_theory"]).casefold()
    assert "pattern completion" in " ".join(queries["neuroscience"]).casefold()
    assert "hysteresis" in " ".join(queries["dynamical_systems"]).casefold()


def test_domain_selection_prioritizes_recurrence_analogues(ml_papers, purpose):
    from gap_mining import mine_gaps

    gap = next(
        item for item in mine_gaps(ml_papers, purpose)
        if "recurring" in item.failure_type
    )
    signature = normalize_cross_domain_problem(gap)
    selected = {
        item.domain for item in select_external_domains(signature)
        if item.selected
    }
    assert {
        "immunology", "ecology", "control_theory", "neuroscience",
        "dynamical_systems",
    } <= selected
