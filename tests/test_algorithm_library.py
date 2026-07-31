from algorithm_library import get_algorithm, load_algorithm_library, weakness_belongs


def test_required_algorithm_coverage():
    library = load_algorithm_library()
    assert len(library) >= 44
    for name in ["naive bayes", "k-means", "gaussian process", "transformer",
                 "diffusion/score models", "neural ode systems"]:
        assert name in library


def test_weakness_binding():
    naive = get_algorithm("Naive Bayes")
    assert weakness_belongs(naive, "conditional independence assumption")
    assert not weakness_belongs(naive, "static coefficients")
