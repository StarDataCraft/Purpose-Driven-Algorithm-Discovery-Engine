from gap_mining import mine_gaps
from search_engine import search_candidates
from signatures import load_mechanism_seeds


def test_structured_candidate_fields(ml_papers, purpose):
    gap = next(g for g in mine_gaps(ml_papers, purpose)
               if g.affected_algorithm == "Random Forest" and "drift" in g.failure_type)
    result = search_candidates(purpose, [gap], load_mechanism_seeds(), 9)
    assert result.candidates
    candidate = result.candidates[0]
    assert candidate.affected_component
    assert candidate.selected_operators
    assert candidate.kill_criterion
    assert candidate.minimal_experiment.failure_rule
    assert candidate.novelty_queries
