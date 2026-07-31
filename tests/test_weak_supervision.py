from weak_supervision import label_sentence


def test_multilabel_and_conflict_handling():
    result = label_sentence(
        "Although we propose a method, a limitation requires complete features at inference time.",
        "discussion",
    )
    assert {"CONTRIBUTION", "LIMITATION", "ASSUMPTION",
            "DEPLOYMENT_CONSTRAINT"} <= set(result.labels)
    assert "contribution_limitation" in result.conflicts


def test_sentence_without_gap_is_not_forced_to_limitation():
    result = label_sentence("Additional parameters appear in Table A.", "appendix")
    assert result.labels == ["OTHER"]
