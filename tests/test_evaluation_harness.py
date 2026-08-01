from dataclasses import asdict
import json
from pathlib import Path
from types import SimpleNamespace

from evaluation.audits import (
    audit_coverage_gap, audit_external_query, audit_mismatch,
    binding_granularity,
)
from evaluation.benchmark_tasks import load_benchmark_tasks
from evaluation.error_analysis import ERROR_TAXONOMY, dominant_bottleneck
from evaluation.report_generation import report_json, report_markdown
from evaluation.retrieval_evaluation import ndcg_at_k, precision_at_k
from evaluation.run_benchmark import run_offline_benchmark
from evaluation.schemas import HumanReview, StageFunnel
from research_memory import ResearchMemory


def test_all_versioned_benchmark_tasks_are_defined():
    tasks = load_benchmark_tasks()
    assert set(tasks) == {
        "recurring_concept_drift", "missingness_shift", "dynamic_clustering"
    }
    assert all(task.version == "1.0.0" for task in tasks.values())
    assert all(task.target_concepts and task.metrics and task.assumptions
               for task in tasks.values())


def test_relevance_metrics_have_expected_semantics():
    labels = [
        "HIGHLY_RELEVANT", "RELEVANT", "IRRELEVANT",
        "PARTIALLY_RELEVANT", "IRRELEVANT",
    ]
    assert precision_at_k(labels, 5) == .4
    assert ndcg_at_k(labels, 5) > 0
    assert ndcg_at_k(sorted(labels), 5) <= 1


def test_review_serialization_and_research_memory(tmp_path):
    review = HumanReview(
        "run:1", "paper:1", "paper", "recurring_concept_drift",
        "RELEVANT", {"confidence": .8}, "reviewer",
        "2026-07-31T00:00:00+00:00", "reviewed", "v1", False,
    )
    serialized = json.loads(json.dumps(asdict(review)))
    assert serialized["label"] == "RELEVANT"
    memory = ResearchMemory(tmp_path / "memory.sqlite")
    memory.save_evaluation_review(review)
    assert memory.evaluation_reviews()[0]["payload"]["run_id"] == "run:1"
    memory.close()


def test_coverage_audit_failure_categories():
    base = dict(
        gap_id="g", cluster_paper_count=10, metadata_completeness=.9,
        expected_relevance=1.0, comparison_cells=[{"cell": 1}],
    )
    assert audit_coverage_gap(
        SimpleNamespace(**{**base, "cluster_paper_count": 4}), live=True
    ).label == "SAMPLE_SIZE_ARTIFACT"
    assert audit_coverage_gap(
        SimpleNamespace(**{**base, "metadata_completeness": .2}), live=True
    ).label == "METADATA_ARTIFACT"
    assert audit_coverage_gap(
        SimpleNamespace(**{**base, "expected_relevance": .2}), live=True
    ).label == "LOGICALLY_IRRELEVANT"
    assert audit_coverage_gap(
        SimpleNamespace(**{**base, "comparison_cells": []}), live=True
    ).label == "WEAK_SUPPORT"
    assert audit_coverage_gap(
        SimpleNamespace(**base), live=True,
        known_solution_status="LIKELY_SOLVED",
    ).label == "LIKELY_ALREADY_ADDRESSED"


def test_mismatch_binding_and_external_query_labels():
    mismatch = SimpleNamespace(
        mismatch_id="m", confidence=.8, contradiction_relation="variant exception",
        observed_condition=SimpleNamespace(evidence_sentence="observed"),
    )
    assert audit_mismatch(mismatch).label == "VARIANT_EXCEPTION"
    assert binding_granularity(SimpleNamespace(
        binding_method="explicit paper mention", confidence=.8,
        family="ensemble",
    )) == "exact algorithm"
    assert audit_external_query(
        "immunology", "online accuracy immune memory"
    ).label == "ML_LANGUAGE_LEAKAGE"
    assert audit_external_query(
        "immunology", "immune memory recurrent exposure"
    ).label == "GOOD"


def test_error_taxonomy_and_funnel_accounting():
    assert "CANDIDATE_UNFALSIFIABLE" in ERROR_TAXONOMY
    assert dominant_bottleneck({
        "ALIGNMENT_SURFACE_ONLY": 4, "QUERY_TOO_BROAD": 1
    }) == "ALIGNMENT"
    funnel = StageFunnel(10, 5, 4, 2, 1, 3, 2, 1, 1)
    assert funnel.rates()["relevant_papers"] == .5
    assert funnel.rates()["valid_gaps"] == .5


def test_offline_end_to_end_evaluation_all_tasks(tmp_path):
    for task in load_benchmark_tasks().values():
        report = run_offline_benchmark(task)
        assert report.run_provenance["actual_search_mode"] == "LIVE"
        assert report.run_provenance["annotations_version"] == "synthetic-ci-v1"
        assert report.query_contributions
        assert report.gap_audits
        assert set(asdict(report.funnel)) == {
            "retrieved_papers", "relevant_papers", "evidence_bearing_papers",
            "valid_gaps", "gaps_surviving_known_solution_checks",
            "relevant_external_papers", "valid_mechanisms",
            "strong_structural_alignments",
            "candidates_surviving_falsification",
            "human_reviewed_papers", "evidence_events",
            "raw_gap_instances", "canonical_gap_families",
            "promoted_directions", "mechanism_bearing_papers",
            "plausible_structural_alignments", "candidate_drafts",
            "final_ideas",
        }
        assert report.funnel.valid_gaps == report.funnel.promoted_directions
        assert report.funnel.canonical_gap_families <= report.funnel.raw_gap_instances
        assert report.funnel.final_ideas <= report.funnel.candidate_drafts
        assert all(
            set(item.score_components) == {
                "problem_specificity", "evidence_strength",
                "algorithm_binding", "mechanism_operationality",
                "modification_specificity", "information_feasibility",
                "novelty_honesty", "falsifiability",
                "experiment_feasibility", "purpose_value",
            }
            for item in report.candidate_audits
        )
        assert "whole-literature recall" in " ".join(report.limitations)
        assert json.loads(report_json(report))["task_id"] == task.task_id
        assert "Automated quality metrics" in report_markdown(report)


def test_no_generative_model_dependency():
    source = "\n".join(
        path.read_text() for path in Path("evaluation").glob("*.py")
    ).casefold()
    assert "openai" not in source
    assert "anthropic" not in source
    assert "generative" not in source
