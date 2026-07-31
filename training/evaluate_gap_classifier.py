"""Evaluate the rule fallback on versioned annotations without model downloads."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from sklearn.metrics import classification_report

from annotation_schema import load_annotations
from sentence_classifier import RuleGapSentenceClassifier
from weak_supervision import GapLabel


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    records = load_annotations(Path(args.data))
    labels = [label.value for label in GapLabel]
    classifier = RuleGapSentenceClassifier()
    truth = [[int(label in record.labels) for label in labels] for record in records]
    predictions = [
        [int(label in classifier.classify(record).labels) for label in labels]
        for record in records
    ]
    report = classification_report(
        truth, predictions, target_names=labels, output_dict=True, zero_division=0
    )
    Path(args.output).write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
