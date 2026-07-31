from models import AlgorithmCandidate
from portfolio import quality_diversity_portfolio


def test_empty_portfolio():
    assert quality_diversity_portfolio([]) == []
