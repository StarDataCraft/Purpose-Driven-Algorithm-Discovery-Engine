from gap_mining import aggregate_gaps, corpus_summary, mine_gaps


def test_section_aware_gap_extraction(ml_papers, purpose):
    gaps = mine_gaps(ml_papers, purpose)
    assert gaps
    assert any(gap.affected_algorithm == "Random Forest" for gap in gaps)
    assert any(gap.gap_type == "explicit" for gap in gaps)
    assert all(gap.evidence_sentences for gap in gaps)


def test_corpus_summary(ml_papers, purpose):
    gaps = mine_gaps(ml_papers, purpose)
    summary = corpus_summary(ml_papers, gaps)
    assert summary["paper_count"] == len(ml_papers)
    assert summary["source_diversity"] == 1
