import pytest

from gap_mining import mine_gaps
from search_engine import search_candidates
from signatures import load_mechanism_seeds


def selected_gap(ml_papers, purpose):
    return next(g for g in mine_gaps(ml_papers, purpose)
                if g.affected_algorithm == "Random Forest" and "drift" in g.failure_type)


def test_contract_preconditions(ml_papers, purpose):
    mechanisms = load_mechanism_seeds()
    with pytest.raises(ValueError, match="PurposeContract"):
        search_candidates(None, [], mechanisms)
    with pytest.raises(ValueError, match="selected gap"):
        search_candidates(purpose, [], mechanisms)
    purpose.primary_metric = ""
    with pytest.raises(ValueError, match="metric"):
        search_candidates(purpose, [mine_gaps(ml_papers, purpose)[0]], mechanisms)


def test_fixed_seed_reproducibility(ml_papers, purpose):
    gap = selected_gap(ml_papers, purpose)
    first = search_candidates(purpose, [gap], load_mechanism_seeds(), 77)
    second = search_candidates(purpose, [gap], load_mechanism_seeds(), 77)
    assert [c.candidate_id for c in first.candidates] == [c.candidate_id for c in second.candidates]
    assert all("machine_learning" not in c.source_domains for c in first.candidates)


def test_three_scales(ml_papers, purpose):
    gap = selected_gap(ml_papers, purpose)
    for scale in ["small", "medium", "large"]:
        result = search_candidates(purpose, [gap], load_mechanism_seeds(), 3, scale)
        assert isinstance(result.rejected_paths, list)
