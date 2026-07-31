"""Deterministic relevance estimates and automatic quality warnings."""

from __future__ import annotations

from hashlib import sha1

from models import Paper, PurposeContract
from run_models import QualityWarning, ResearchRun


def estimate_paper_relevance(
    paper: Paper, purpose: PurposeContract
) -> tuple[float, str]:
    """Estimate relevance without pretending to be human review."""
    text = f"{paper.title} {paper.abstract}".casefold()
    task_terms = {
        token for token in purpose.task.casefold().split() if len(token) > 3
    }
    failure_terms = {
        token for token in purpose.current_failure.casefold().split()
        if len(token) > 3
    }
    capability_terms = {
        token for token in purpose.desired_improvement.casefold().split()
        if len(token) > 3
    }
    title = paper.title.casefold()
    task = sum(term in text for term in task_terms) / max(1, len(task_terms))
    failure = sum(term in text for term in failure_terms) / max(1, len(failure_terms))
    capability = sum(term in text for term in capability_terms) / max(
        1, len(capability_terms)
    )
    title_match = sum(term in title for term in failure_terms) / max(
        1, len(failure_terms)
    )
    score = round(
        min(1.0, .25 * task + .4 * failure + .2 * capability + .15 * title_match),
        4,
    )
    label = (
        "ESTIMATED_HIGH" if score >= .7
        else "ESTIMATED_MEDIUM" if score >= .45
        else "ESTIMATED_LOW" if score >= .2
        else "ESTIMATED_IRRELEVANT"
    )
    return score, label


def apply_estimated_relevance(
    papers: list[Paper], purpose: PurposeContract
) -> list[Paper]:
    for paper in papers:
        paper.estimated_relevance_score, paper.estimated_relevance_label = (
            estimate_paper_relevance(paper, purpose)
        )
        # Human labels are never synthesized or overwritten.
        if not paper.reviewed_relevance_label:
            paper.review_status = "UNREVIEWED"
    return papers


def warning(
    stage: str, code: str, title: str, explanation: str,
    observed: object, expected: str, action: str, severity: str = "warning",
) -> QualityWarning:
    identifier = sha1(
        f"{stage}:{code}:{observed}".encode()
    ).hexdigest()[:12]
    return QualityWarning(
        f"warning:{identifier}", severity, stage, code, title, explanation,
        str(observed), expected, action,
    )


def generate_quality_warnings(run: ResearchRun) -> list[QualityWarning]:
    warnings: list[QualityWarning] = []
    candidates = run.candidate_paper_count
    automatic = run.automatically_relevant_paper_count
    ratio = automatic / max(1, candidates)
    if candidates and automatic == candidates:
        warnings.append(warning(
            "paper_reranking", "ALL_CANDIDATES_AUTOMATICALLY_RELEVANT",
            "Every candidate paper passed automatic relevance",
            "Automatic relevance may be uncalibrated or the threshold too permissive.",
            f"{automatic}/{candidates}", "less than all candidate papers",
            "Review top and bottom ranked papers before treating the corpus as relevant.",
        ))
    elif candidates >= 20 and ratio > .9:
        warnings.append(warning(
            "paper_reranking", "SUSPICIOUS_RELEVANCE_RATIO",
            "Automatic relevance ratio is unusually high",
            "A broad live corpus rarely contains almost no low-relevance papers.",
            round(ratio, 3), "≤ 0.90", "Review threshold calibration.",
        ))
    if (
        run.raw_gap_instance_count > candidates
        and run.canonical_gap_family_count == 0
    ):
        warnings.append(warning(
            "gap_consolidation", "UNCONSOLIDATED_GAP_VOLUME",
            "Raw gap instances exceed the paper corpus",
            "Raw instances must not be presented as distinct research gaps.",
            run.raw_gap_instance_count, f"families derived from {candidates} papers",
            "Run consolidation and promotion before gap selection.",
        ))
    if (
        run.evidence_bearing_paper_count
        and run.raw_gap_instance_count / run.evidence_bearing_paper_count > 5
    ):
        warnings.append(warning(
            "gap_extraction", "HIGH_GAPS_PER_EVIDENCE_PAPER",
            "Many gap instances came from each evidence paper",
            "Cue duplication or overlapping structural detectors may inflate output.",
            round(run.raw_gap_instance_count / run.evidence_bearing_paper_count, 2),
            "≤ 5 raw instances per evidence-bearing paper",
            "Inspect raw evidence events and family membership.",
        ))
    if run.external_query_count and run.stages:
        external = [
            stage for stage in run.stages if stage.stage_name == "external_retrieval"
        ]
        if external and external[-1].actual_mode == "CACHE":
            warnings.append(warning(
                "external_retrieval", "CACHE_ONLY_EXTERNAL_EVIDENCE",
                "External evidence came entirely from cache",
                "Cached evidence may be valid but is not a fresh external search.",
                external[-1].output_count, "freshness shown per cache entry",
                "Review cache ages or force a fresh external search.", "info",
            ))
    if run.expired_cache_count:
        warnings.append(warning(
            "retrieval", "STALE_CACHE", "Expired cache entries were used",
            "Expired evidence requires explicit permission and freshness disclosure.",
            run.expired_cache_count, "0 expired entries",
            "Refresh or document explicit stale-cache acceptance.",
        ))
    if run.human_reviewed_paper_count == 0 and run.actual_search_mode in {
        "LIVE", "MIXED", "CACHE"
    }:
        warnings.append(warning(
            "paper_reranking", "UNREVIEWED_LIVE_RUN",
            "Live literature relevance is unreviewed",
            "Automatic estimates are not validated human relevance labels.",
            0, "at least a reviewed sample",
            "Review a stratified sample before making quality claims.", "info",
        ))
    if run.alignment_funnel and not (
        run.alignment_funnel.get("strong_alignment_count")
        or run.alignment_funnel.get("strong")
    ):
        warnings.append(warning(
            "structural_alignment", "NO_STRONG_ALIGNMENT",
            "No strong structural alignment was found",
            "Candidates should require a strong or explicitly accepted plausible path.",
            0, "≥ 1 strong alignment",
            "Review plausible alignments or stop candidate promotion.",
        ))
    run.quality_warnings = warnings
    run.warnings = list(dict.fromkeys(
        [*run.warnings, *(item.title for item in warnings)]
    ))
    return warnings
