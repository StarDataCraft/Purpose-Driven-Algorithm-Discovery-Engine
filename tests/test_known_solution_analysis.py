from gap_mining import mine_gaps
from known_solution_analysis import assess_known_solutions, known_solution_queries


def test_known_solution_queries_and_scope(ml_papers, purpose):
    gap = mine_gaps(ml_papers, purpose)[0]
    queries = known_solution_queries(gap)
    assert any(gap.affected_algorithm in query for query in queries)
    result = assess_known_solutions(gap, ml_papers)
    assert result.search_coverage.startswith("local retrieved corpus")
    assert result.status in {"partially addressed", "insufficient evidence"}
