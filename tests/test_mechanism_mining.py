from mechanism_mining import cross_domain_only, extract_mechanisms, validate_mechanism_phrase
from models import MechanismSignature


def test_invalid_mechanisms_are_rejected():
    for phrase in ["higher", "proposed", "effective", "research", "significant",
                   "novel", "improved", "performance"]:
        assert not validate_mechanism_phrase(phrase, "biology")[0]


def test_valid_mechanisms_are_recognized():
    phrases = [
        "homeostatic negative feedback", "immune memory reactivation",
        "predictive error correction", "observability-based state estimation",
        "mechanism-design incentive alignment", "phase-transition threshold switching",
        "ecological niche competition", "resource allocation feedback",
        "specialist reactivation memory",
    ]
    for phrase in phrases:
        assert validate_mechanism_phrase(phrase, "biology")[0], phrase


def test_external_fixture_extracts_evidence(external_papers):
    mechanisms, rejected = extract_mechanisms(external_papers)
    names = {mechanism.name for mechanism in mechanisms}
    assert "immune memory reactivation" in names
    assert "ecological niche competition" in names
    assert all(mechanism.evidence_sentences for mechanism in mechanisms)


def test_machine_learning_excluded():
    sample = MechanismSignature(
        "x", "feedback memory", "machine_learning", "x", [], "x", "x", "x", "x",
        "x", "x", "x", "x", "x", "x", "x", "x", "dynamic weighting",
        ["update_rule"], [], [], ["evidence"], ["abstract"], ["p"], 1, .8,
    )
    assert cross_domain_only([sample]) == []
