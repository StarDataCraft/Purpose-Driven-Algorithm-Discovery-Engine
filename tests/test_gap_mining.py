from dataclasses import replace

from gap_mining import aggregate_gaps, corpus_summary, mine_gaps
from models import Paper


def test_section_aware_gap_extraction(ml_papers, purpose):
    gaps = mine_gaps(ml_papers, purpose)
    assert gaps
    assert any(gap.affected_algorithm == "Random Forest" for gap in gaps)
    assert any(gap.gap_type == "explicit" for gap in gaps)
    assert all(gap.evidence_sentences for gap in gaps)


def test_corpus_summary(ml_papers, purpose):
    gaps = mine_gaps(ml_papers, purpose)
    summary = corpus_summary(ml_papers, gaps)
    assert summary["paper_count"] == len(ml_papers)
    assert summary["source_diversity"] == 1


def test_selected_generic_algorithm_family_is_not_dropped(purpose):
    selected = replace(
        purpose, allowed_algorithm_families=["tree ensemble"],
        current_failure="training inference missingness shift",
    )
    papers = [Paper(
        "p", "Tree ensemble under missingness shift",
        "However, prediction fails when inference features are missing.",
        2025, "fixture", sections={
            "limitations": "However, prediction fails when inference features are missing."
        },
    )]
    gaps = mine_gaps(papers, selected)
    assert gaps
    assert all(gap.affected_algorithm_family == "tree ensemble" for gap in gaps)
    assert all(gap.affected_component == "feature_acquisition" for gap in gaps)
