import numpy as np

from gap_mining import mine_gaps
from semantic_gap_aggregation import aggregate_semantic_gaps


def test_paraphrases_aggregate_but_structural_variants_do_not(ml_papers, purpose):
    gaps = mine_gaps(ml_papers, purpose)
    compatible = [gap for gap in gaps if gap.affected_algorithm == "Random Forest"][:2]
    compatible[1].failure_type = compatible[0].failure_type
    compatible[1].affected_component = compatible[0].affected_component
    compatible[1].structural_gap_subtype = compatible[0].structural_gap_subtype
    embeddings = np.array([[1., 0.], [.99, .01]])
    families = aggregate_semantic_gaps(compatible, embeddings, .8)
    assert len(families) == 1
    compatible[1].affected_component = "memory"
    families = aggregate_semantic_gaps(compatible, embeddings, .8)
    assert len(families) == 2
