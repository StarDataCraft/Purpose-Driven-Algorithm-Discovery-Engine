from alignment import align
from gap_mining import mine_gaps
from scoring import score_candidate
from signatures import load_mechanism_seeds


def test_score_components_are_exposed(ml_papers, purpose):
    gap = mine_gaps(ml_papers, purpose)[0]
    mechanism = load_mechanism_seeds()[0]
    result = align(gap, mechanism, purpose)
    card = score_candidate(gap, result, purpose_fit=.8, feasibility=.8,
                           testability=.8, novelty=.6, diversity=.7)
    assert "purpose_fit" in card.components
    assert "inference_leakage" in card.penalties
    assert 0 <= card.total <= 1
