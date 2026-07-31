"""Falsification-first checks that execute before candidate promotion."""

from __future__ import annotations

from models import GapSignature, MechanismSignature, Operator, PurposeContract

FORBIDDEN_INFERENCE = {
    "clean labels", "clean label", "future observations", "future observation",
    "hidden ground-truth states", "ground truth state", "ground-truth state",
}

SIGNAL_EQUIVALENTS = {
    "observable deviation": {"prediction residual", "observable error"},
    "performance signal": {"prediction residual", "online error", "observed loss"},
    "observation innovation": {"prediction residual", "observable error"},
    "regime similarity": {"context similarity", "recurrence score"},
}


def information_leakage(required: list[str], available: list[str]) -> list[str]:
    available_text = " ".join(available).casefold()
    failures = []
    for signal in required:
        lower = signal.casefold()
        if any(term in lower for term in FORBIDDEN_INFERENCE):
            failures.append(f"forbidden inference information: {signal}")
        elif (
            signal not in available
            and not any(
                token in available_text for token in lower.split() if len(token) > 4
            )
            and not any(
                equivalent in available_text
                for equivalent in SIGNAL_EQUIVALENTS.get(lower, set())
            )
        ):
            failures.append(f"unavailable inference information: {signal}")
    return failures


def preflight_rejections(purpose: PurposeContract | None, gap: GapSignature | None,
                         mechanism: MechanismSignature, operator: Operator) -> list[str]:
    reasons = []
    if purpose is None:
        reasons.append("missing purpose contract")
        return reasons
    if gap is None:
        reasons.append("missing selected gap")
        return reasons
    if not purpose.primary_metric:
        reasons.append("missing evaluation metric")
    if not purpose.available_inference_information:
        reasons.append("missing inference information definition")
    reasons.extend(information_leakage(
        list(dict.fromkeys(mechanism.required_signal + operator.inference_requirements)),
        purpose.available_inference_information,
    ))
    if gap.affected_component not in operator.compatible_slots:
        reasons.append("operator-slot incompatibility")
    if mechanism.source_domain == "machine_learning":
        reasons.append("false cross-disciplinarity")
    if not mechanism.evidence_sentences:
        reasons.append("mechanism has no source evidence")
    return reasons


def falsification_tests(base: str, operator: Operator, mechanism: MechanismSignature) -> list[str]:
    return [
        f"Compare {base} against the full modification under matched compute.",
        "Replace the mechanism signal with a random permutation; comparable gains reject the mechanism claim.",
        "Use a fixed non-adaptive version; comparable gains reject the adaptive explanation.",
        f"Compare with the simplest known equivalent: {', '.join(operator.known_equivalent_ml_patterns)}.",
        "Match parameter count and report whether added capacity alone explains the gain.",
        f"Stress the mechanism failure boundary: {mechanism.failure_boundary}.",
    ]
