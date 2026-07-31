"""Versioned sentence annotation records and bounded context construction."""

from __future__ import annotations

import csv
import io
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class SentenceAnnotation:
    sentence_id: str
    paper_id: str
    section: str
    previous_sentence: str
    target_sentence: str
    next_sentence: str
    labels: list[str]
    annotator: str
    annotation_version: str
    adjudication_status: str
    reviewer_confidence: float = 0.0
    notes: str = ""


def context_window(annotation: SentenceAnnotation, max_characters: int = 3000) -> str:
    text = (
        f"[SECTION] {annotation.section}\n"
        f"[PREV] {annotation.previous_sentence}\n"
        f"[TARGET] {annotation.target_sentence}\n"
        f"[NEXT] {annotation.next_sentence}"
    )
    return text[:max_characters]


def load_annotations(path: Path, limit: int = 1000) -> list[SentenceAnnotation]:
    records = []
    with path.open() as handle:
        for line in handle:
            if line.strip():
                records.append(SentenceAnnotation(**json.loads(line)))
            if len(records) >= limit:
                break
    return records


def annotations_jsonl(records: list[SentenceAnnotation]) -> str:
    return "\n".join(json.dumps(asdict(record)) for record in records)


def annotations_csv(records: list[SentenceAnnotation]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=asdict(records[0]).keys() if records else [])
    if records:
        writer.writeheader()
        for record in records:
            row = asdict(record)
            row["labels"] = "|".join(row["labels"])
            writer.writerow(row)
    return output.getvalue()
