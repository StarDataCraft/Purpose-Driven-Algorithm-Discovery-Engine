from direction_families import create_direction_families
from gap_mining import mine_gaps
from mechanism_mining import cross_domain_only, extract_mechanisms
from portfolio import quality_diversity_portfolio
from search_engine import search_candidates


def test_offline_end_to_end(ml_papers, external_papers, purpose):
    gaps = mine_gaps(ml_papers, purpose)
    mechanisms, rejected = extract_mechanisms(external_papers)
    mechanisms = cross_domain_only(mechanisms)
    selected = [gap for gap in gaps if gap.affected_algorithm == "Random Forest"]
    result = search_candidates(purpose, selected[:2], mechanisms, seed=47, scale="small")
    portfolio = quality_diversity_portfolio(result.candidates)
    families = create_direction_families(portfolio)
    assert portfolio
    assert families
    assert any("immune" in " ".join(c.borrowed_mechanisms) for c in portfolio)
    assert all(c.evidence_paper_ids for c in portfolio)
    assert all(c.minimal_experiment.hypothesis for c in portfolio)
