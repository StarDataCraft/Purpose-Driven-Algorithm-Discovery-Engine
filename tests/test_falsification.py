from falsification import information_leakage


def test_inference_leakage_rejection():
    failures = information_leakage(
        ["clean labels", "future observations", "hidden ground-truth states"],
        ["input features"],
    )
    assert len(failures) == 3


def test_available_signal_passes():
    assert information_leakage(["regime similarity"], ["regime similarity"]) == []
