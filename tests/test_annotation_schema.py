from pathlib import Path

from annotation_schema import load_annotations


def test_seed_annotations_are_versioned_and_multilabel():
    path = Path(__file__).resolve().parents[1] / "data/annotations/gap_sentences.jsonl"
    records = load_annotations(path)
    assert len(records) == 13
    assert all(record.annotation_version == "1.0" for record in records)
    assert any(len(record.labels) > 1 for record in records)
