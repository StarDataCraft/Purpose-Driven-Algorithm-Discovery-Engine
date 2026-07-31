from algorithm_library import get_algorithm
from experiment_planner import build_experiment
from gap_mining import mine_gaps


def test_plan_has_required_ablations(ml_papers, purpose):
    gap = next(g for g in mine_gaps(ml_papers, purpose) if g.affected_algorithm == "Random Forest")
    plan = build_experiment(purpose, gap, get_algorithm("Random Forest"), "candidate")
    joined = " ".join(plan.ablations)
    for expected in ["base algorithm", "shuffled", "fixed non-adaptive",
                     "full adaptive", "parameter-count", "operator-only"]:
        assert expected in joined
    assert plan.success_rule and plan.failure_rule and len(plan.seeds) >= 3
