"""Thin Streamlit UI for the no-LLM purpose-driven discovery pipeline."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date
from pathlib import Path
from uuid import uuid4

import streamlit as st

from algorithm_library import load_algorithm_library
from alignment import align
from config import DEFAULT_DB, FIXTURE_DIR
from direction_families import create_direction_families
from gap_mining import corpus_summary, mine_gaps
from io_utils import experiment_to_markdown, records_to_csv, to_json
from mechanism_mining import cross_domain_only, extract_mechanisms
from models import Paper, PurposeContract
from paper_fetchers import fetch_papers_cached
from portfolio import quality_diversity_portfolio
from query_generation import generate_external_queries, generate_ml_queries
from research_memory import ResearchMemory
from search_engine import search_candidates
from signatures import load_mechanism_seeds
from trend_analysis import trend_indicators

PAGES = [
    "1 · Goal setup", "2 · Latest ML/DL gap radar", "3 · Gap evidence",
    "4 · External mechanism search", "5 · Structural alignment",
    "6 · Research direction families", "7 · Candidate algorithms",
    "8 · Novelty and falsification", "9 · Minimal experiment",
    "10 · Research memory",
]


def load_fixture(name: str) -> list[Paper]:
    return [Paper(**item) for item in json.loads((FIXTURE_DIR / name).read_text())]


def initialize_state() -> None:
    defaults = {
        "purpose": None, "ml_papers": [], "gaps": [], "selected_gap": None,
        "external_papers": [], "mechanisms": [], "rejected_mechanisms": [],
        "alignments": [], "candidates": [], "families": [], "fetch_failures": {},
        "external_queries": {}, "seed": 42,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def sidebar() -> str:
    st.sidebar.title("目的驱动 · Discovery Engine")
    st.sidebar.caption("No LLMs. Evidence → purpose → mechanism → experiment.")
    return st.sidebar.radio("Workflow", PAGES, key="_workflow_page")


def goal_page() -> None:
    st.title("Purpose contract")
    mode = st.radio(
        "Mode", ["User-defined purpose", "Gap radar"], key="_purpose_mode"
    )
    with st.form("_purpose_form"):
        col1, col2 = st.columns(2)
        task = col1.text_input("Task", "online learning", key="_purpose_task")
        data_type = col2.text_input(
            "Data type", "tabular streams", key="_purpose_data_type"
        )
        use_case = col1.text_input(
            "Application", "adaptive decision support", key="_purpose_use_case"
        )
        failure = col2.text_input(
            "Current failure", "recurring concept drift", key="_purpose_failure"
        )
        improvement = col1.text_input(
            "Desired improvement",
            "reduce post-shift recovery time",
            key="_purpose_improvement",
        )
        metric = col2.text_input(
            "Primary metric", "average online accuracy", key="_purpose_metric"
        )
        secondary = col1.text_input(
            "Secondary metrics",
            "recovery time, memory use",
            key="_purpose_secondary",
        )
        preserve = col2.text_input(
            "Must not degrade",
            "stable-regime accuracy, calibration",
            key="_purpose_preserve",
        )
        training = col1.text_input(
            "Training information",
            "features, delayed outcome feedback",
            key="_purpose_training",
        )
        inference = col2.text_input(
            "Inference information",
            "input features, prediction residual, regime similarity",
            key="_purpose_inference",
        )
        algorithm = st.selectbox(
            "Affected algorithm",
            sorted(load_algorithm_library()),
            key="_purpose_algorithm",
        )
        risk = col1.selectbox(
            "Risk tolerance",
            ["low", "medium", "high"],
            index=1,
            key="_purpose_risk",
        )
        scale = col2.selectbox(
            "Combination scale",
            ["small", "medium", "large"],
            key="_purpose_scale",
        )
        years = st.slider(
            "Publication window",
            2018,
            date.today().year,
            (2022, date.today().year),
            key="_purpose_years",
        )
        offline = st.checkbox(
            "Use bundled offline evidence (reproducible demo)",
            value=True,
            key="_purpose_offline",
        )
        submitted = st.form_submit_button(
            "Discover ML/DL gaps", type="primary"
        )
    if submitted:
        record = load_algorithm_library()[algorithm]
        purpose = PurposeContract(
            purpose_id=f"purpose:{uuid4().hex[:10]}",
            mode="user" if mode.startswith("User") else "gap_radar",
            use_case=use_case, task=task, data_type=data_type, current_failure=failure,
            desired_improvement=improvement, primary_metric=metric,
            secondary_metrics=[x.strip() for x in secondary.split(",") if x.strip()],
            must_not_degrade=[x.strip() for x in preserve.split(",") if x.strip()],
            available_training_information=[x.strip() for x in training.split(",") if x.strip()],
            available_inference_information=[x.strip() for x in inference.split(",") if x.strip()],
            allowed_algorithm_families=[record.family], risk_tolerance=risk,
            preferred_candidate_scale=scale, publication_window=years,
        )
        st.session_state.purpose = purpose
        if offline:
            papers, failures = load_fixture("ml_papers.json"), {}
        else:
            queries = generate_ml_queries(purpose, record.name)
            papers, failures = fetch_papers_cached(
                " OR ".join(queries[:3]), ["openalex", "arxiv"], 30, *years
            )
        st.session_state.ml_papers = papers
        st.session_state.fetch_failures = failures
        st.session_state.gaps = mine_gaps(papers, purpose)
        st.success(f"Mined {len(st.session_state.gaps)} gap records from {len(papers)} papers.")


def gap_radar_page() -> None:
    st.title("Latest ML/DL gap radar")
    gaps = st.session_state.gaps
    if not gaps:
        st.info("Create a purpose contract and discover gaps first.")
        return
    st.json(corpus_summary(st.session_state.ml_papers, gaps))
    labels = {
        f"{g.title} · {g.gap_type} · confidence {g.confidence_score:.2f} · evidence {g.evidence_count}": g
        for g in sorted(gaps, key=lambda x: (x.confidence_score, x.evidence_count), reverse=True)
    }
    chosen = st.selectbox(
        "Select an evidence-backed gap", labels, key="_gap_radar_selection"
    )
    if st.button("Use selected gap", type="primary", key="_gap_radar_submit"):
        st.session_state.selected_gap = labels[chosen]
        st.success("Gap selected. Continue to evidence or external mechanism search.")
    st.dataframe([{
        "gap": g.title, "type": g.gap_type, "algorithm": g.affected_algorithm,
        "failure": g.failure_type, "evidence": g.evidence_count,
        "confidence": g.confidence_score, "testability": g.testability_score,
    } for g in gaps], use_container_width=True)


def evidence_page() -> None:
    st.title("Gap evidence")
    gap = st.session_state.selected_gap
    if not gap:
        st.info("Select a gap in the radar.")
        return
    st.subheader(gap.title)
    st.write({
        "task": gap.task, "current method": gap.current_method_pattern,
        "failure condition": gap.failure_type, "observable signal": gap.observable_failure_signal,
        "why it matters / response": gap.required_response, "assumptions": gap.unresolved_assumptions,
        "must preserve": gap.must_preserve, "missing evidence": [] if gap.evidence_count > 1 else ["independent corroboration"],
    })
    for sentence, section, paper_id in zip(
        gap.evidence_sentences, gap.evidence_sections, gap.evidence_paper_ids
    ):
        st.markdown(f"> {sentence}\n\nSection: `{section}` · Paper: `{paper_id}`")


def mechanism_page() -> None:
    st.title("External mechanism search")
    gap = st.session_state.selected_gap
    if not gap:
        st.info("Select a verified gap first.")
        return
    queries = generate_external_queries(gap)
    st.session_state.external_queries = queries
    st.json(queries)
    offline = st.checkbox(
        "Use bundled external evidence", value=True, key="_mechanism_offline"
    )
    if st.button(
        "Fetch and extract mechanisms", type="primary", key="_mechanism_fetch"
    ):
        papers = load_fixture("external_papers.json") if offline else []
        failures = {}
        if not offline:
            for domain, domain_queries in queries.items():
                fetched, failed = fetch_papers_cached(
                    domain_queries[0], ["openalex", "arxiv"], 6,
                    *st.session_state.purpose.publication_window
                )
                for paper in fetched:
                    paper.domain = domain
                papers.extend(fetched)
                failures.update({f"{domain}:{key}": value for key, value in failed.items()})
        mechanisms, rejected = extract_mechanisms(papers)
        if not mechanisms:
            mechanisms = load_mechanism_seeds()
        st.session_state.external_papers = papers
        st.session_state.mechanisms = cross_domain_only(mechanisms)
        st.session_state.rejected_mechanisms = rejected
        st.session_state.fetch_failures.update(failures)
    st.dataframe([{
        "mechanism": m.name, "domain": m.source_domain,
        "signal": m.observed_signal, "response": m.response_rule,
        "evidence": m.evidence_count, "confidence": m.confidence_score,
    } for m in st.session_state.mechanisms], use_container_width=True)
    st.caption(f"Rejected invalid phrases: {len(st.session_state.rejected_mechanisms)}")
    with st.expander("Rejected extraction details"):
        st.json(st.session_state.rejected_mechanisms)


def alignment_page() -> None:
    st.title("Structural alignment")
    gap, mechanisms = st.session_state.selected_gap, st.session_state.mechanisms
    if not gap or not mechanisms:
        st.info("Select a gap and extract mechanisms first.")
        return
    results = [align(gap, mechanism, st.session_state.purpose) for mechanism in mechanisms]
    st.session_state.alignments = results
    st.dataframe([{
        "mechanism": result.mechanism_id, "score": round(result.score, 2),
        "slot": ", ".join(result.matched_slots), "rejected": result.rejected,
        "conflicts": "; ".join(result.conflicts),
        "missing": "; ".join(result.missing_information),
    } for result in results], use_container_width=True)
    for result in results:
        with st.expander(result.mechanism_id):
            st.json(asdict(result))


def generate_candidates() -> None:
    memory = ResearchMemory(DEFAULT_DB)
    result = search_candidates(
        st.session_state.purpose, [st.session_state.selected_gap],
        st.session_state.mechanisms, st.session_state.seed,
        st.session_state.purpose.preferred_candidate_scale, 24,
        memory.failure_penalties(),
    )
    memory.close()
    portfolio = quality_diversity_portfolio(result.candidates, 12)
    st.session_state.candidates = portfolio
    st.session_state.rejected_paths = result.rejected_paths
    st.session_state.families = create_direction_families(portfolio)


def family_page() -> None:
    st.title("Research direction families")
    if st.button(
        "Run stochastic structured search", type="primary", key="_family_search"
    ):
        generate_candidates()
    if not st.session_state.families:
        st.info("Run search after selecting a gap and mechanisms.")
        return
    for family in st.session_state.families:
        with st.expander(f"{family.name} · risk {family.risk_level}", expanded=True):
            st.json(asdict(family))


def candidates_page() -> None:
    st.title("Candidate algorithms")
    st.session_state.setdefault("_candidate_seed", st.session_state.seed)
    seed = st.number_input(
        "Reproducible seed", step=1, key="_candidate_seed"
    )
    st.session_state.seed = int(seed)
    if st.button(
        "Regenerate portfolio", type="primary", key="_candidate_regenerate"
    ):
        generate_candidates()
    for candidate in st.session_state.candidates:
        with st.expander(f"{candidate.candidate_name} · {candidate.confidence}", expanded=True):
            st.write({
                "scale": candidate.stochastic_trace["search_scale"],
                "base algorithm": candidate.base_algorithm, "gap": candidate.gap_summary,
                "mechanisms": candidate.borrowed_mechanisms, "slot": candidate.affected_component,
                "operators": candidate.selected_operators, "new state": candidate.new_state_variables,
                "expected improvement": candidate.expected_improvement,
                "must not degrade": candidate.must_not_degrade,
                "inference information": candidate.required_inference_information,
                "risk / failure modes": candidate.expected_failure_modes,
            })
            st.json(asdict(candidate.scores))
            st.caption(f"Sampled path: {candidate.stochastic_trace['sampled_structural_path']}")


def novelty_page() -> None:
    st.title("Novelty and falsification")
    for candidate in st.session_state.candidates:
        with st.expander(candidate.candidate_name):
            st.write({
                "novelty status": candidate.novelty_status,
                "structural fingerprint": candidate.structural_fingerprint or "computed on export",
                "nearest known methods": candidate.nearest_known_method_patterns,
                "novelty queries": candidate.novelty_queries,
                "strongest rejection reason": candidate.strongest_rejection_reason,
                "kill criterion": candidate.kill_criterion,
                "information audit": candidate.minimal_experiment.information_audit,
            })
            st.markdown("\n".join(f"- {test}" for test in candidate.falsification_tests))
    with st.expander("Rejected search paths"):
        st.json(st.session_state.get("rejected_paths", []))


def experiment_page() -> None:
    st.title("Minimal experiment")
    candidates = st.session_state.candidates
    if not candidates:
        st.info("Generate candidates first.")
        return
    labels = {candidate.candidate_name: candidate for candidate in candidates}
    candidate = labels[
        st.selectbox("Candidate", labels, key="_experiment_candidate")
    ]
    st.json(asdict(candidate.minimal_experiment))
    st.download_button(
        "Download JSON",
        to_json(candidate.minimal_experiment),
        f"{candidate.candidate_id.replace(':', '-')}-experiment.json",
        key="_experiment_download_json",
    )
    st.download_button(
        "Download Markdown",
        experiment_to_markdown(candidate.minimal_experiment),
        f"{candidate.candidate_id.replace(':', '-')}-experiment.md",
        key="_experiment_download_markdown",
    )


def memory_page() -> None:
    st.title("Research memory")
    memory = ResearchMemory(DEFAULT_DB)
    if st.button("Save current run", key="_memory_save"):
        for gap in st.session_state.gaps:
            memory.save("gap", gap.gap_id, gap)
        for mechanism in st.session_state.mechanisms:
            memory.save("mechanism", mechanism.mechanism_id, mechanism)
        for family in st.session_state.families:
            memory.save("direction_family", family.family_id, family)
        for candidate in st.session_state.candidates:
            memory.save("candidate", candidate.candidate_id, candidate)
        for index, rejection in enumerate(st.session_state.get("rejected_paths", [])):
            fingerprint = "|".join(str(rejection.get(key, ""))
                                   for key in ("gap", "mechanism", "operator"))
            memory.remember_failure(fingerprint, "weak evidence", json.dumps(rejection))
        st.success("Saved gaps, mechanisms, families, candidates, and failures.")
    tabs = st.tabs(["Gaps", "Mechanisms", "Families", "Candidates", "Failures"])
    for tab, kind in zip(tabs[:4], ["gap", "mechanism", "direction_family", "candidate"]):
        tab.json(memory.list(kind))
    tabs[4].json(memory.failures())
    exported = {
        kind: memory.list(kind) for kind in ("gap", "mechanism", "direction_family", "candidate")
    }
    st.download_button(
        "Export memory JSON",
        json.dumps(exported, indent=2),
        "research-memory.json",
        key="_memory_download_json",
    )
    flat = [{"kind": kind, **record} for kind, records in exported.items() for record in records]
    st.download_button(
        "Export memory CSV",
        records_to_csv(flat),
        "research-memory.csv",
        key="_memory_download_csv",
    )
    markdown = "# Research memory\n\n" + "\n\n".join(
        f"## {kind.replace('_', ' ').title()}\n\n```json\n{json.dumps(records, indent=2)}\n```"
        for kind, records in exported.items()
    )
    st.download_button(
        "Export memory Markdown",
        markdown,
        "research-memory.md",
        key="_memory_download_markdown",
    )
    memory.close()


def main() -> None:
    st.set_page_config(page_title="Purpose-Driven Algorithm Discovery", layout="wide")
    initialize_state()
    page = sidebar()
    handlers = [goal_page, gap_radar_page, evidence_page, mechanism_page, alignment_page,
                family_page, candidates_page, novelty_page, experiment_page, memory_page]
    handlers[PAGES.index(page)]()
    if st.session_state.ml_papers:
        with st.sidebar.expander("Trend radar"):
            st.json(trend_indicators(st.session_state.ml_papers + st.session_state.external_papers))
    if st.session_state.fetch_failures:
        st.sidebar.warning("Partial source failures occurred; available results remain usable.")
        st.sidebar.json(st.session_state.fetch_failures)


if __name__ == "__main__":
    main()
