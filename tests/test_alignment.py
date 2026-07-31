from alignment import align
from gap_mining import mine_gaps
from signatures import load_mechanism_seeds


def test_compatible_slots_score_higher(ml_papers, purpose):
    gap = next(g for g in mine_gaps(ml_papers, purpose) if g.affected_algorithm == "Random Forest")
    mechanisms = {m.mechanism_id: m for m in load_mechanism_seeds()}
    gap.affected_component = "memory"
    compatible = align(gap, mechanisms["immune_memory"], purpose)
    gap.affected_component = "objective"
    incompatible = align(gap, mechanisms["immune_memory"], purpose)
    assert compatible.score > incompatible.score
    assert incompatible.rejected


def test_false_cross_domain_rejected(ml_papers, purpose):
    gap = mine_gaps(ml_papers, purpose)[0]
    mechanism = load_mechanism_seeds()[0]
    mechanism.source_domain = "machine_learning"
    assert align(gap, mechanism, purpose).rejected
