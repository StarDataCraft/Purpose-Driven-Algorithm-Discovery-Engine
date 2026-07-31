"""Reproducible local fine-tuning entry point for a multi-label SciBERT classifier."""

from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path

import numpy as np

from annotation_schema import context_window, load_annotations
from weak_supervision import GapLabel


def split_by_paper(records, seed: int = 42):
    papers = sorted({record.paper_id for record in records})
    random.Random(seed).shuffle(papers)
    n = len(papers)
    train_ids = set(papers[:max(1, int(.7*n))])
    validation_ids = set(papers[max(1, int(.7*n)):max(2, int(.85*n))])
    return (
        [r for r in records if r.paper_id in train_ids],
        [r for r in records if r.paper_id in validation_ids],
        [r for r in records if r.paper_id not in train_ids | validation_ids],
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    records = load_annotations(Path(args.train))
    train, validation, test = split_by_paper(records, args.seed)
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    try:
        import torch
        from sklearn.metrics import f1_score, precision_recall_fscore_support
        from transformers import (
            AutoModelForSequenceClassification, AutoTokenizer,
            EarlyStoppingCallback, Trainer, TrainingArguments,
        )
    except ImportError as exc:
        raise SystemExit(
            "Install requirements-enhanced.txt before training SciBERT."
        ) from exc
    labels = [label.value for label in GapLabel]
    label_to_id = {label: index for index, label in enumerate(labels)}
    tokenizer = AutoTokenizer.from_pretrained("allenai/scibert_scivocab_uncased")

    class AnnotationDataset(torch.utils.data.Dataset):
        def __init__(self, rows):
            self.rows = rows
            self.encodings = tokenizer(
                [context_window(row) for row in rows],
                truncation=True, padding=True, max_length=512,
            )
            self.targets = [
                [float(label in row.labels) for label in labels] for row in rows
            ]

        def __len__(self):
            return len(self.rows)

        def __getitem__(self, index):
            item = {
                key: torch.tensor(value[index])
                for key, value in self.encodings.items()
            }
            item["labels"] = torch.tensor(self.targets[index], dtype=torch.float)
            return item

    model = AutoModelForSequenceClassification.from_pretrained(
        "allenai/scibert_scivocab_uncased", num_labels=len(labels),
        problem_type="multi_label_classification",
        id2label={index: label for label, index in label_to_id.items()},
        label2id=label_to_id,
    )
    train_counts = np.array([
        sum(label in row.labels for row in train) for label in labels
    ], dtype=float)
    positive_weights = torch.tensor(
        (len(train) - train_counts) / np.maximum(train_counts, 1),
        dtype=torch.float,
    )

    class WeightedTrainer(Trainer):
        def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
            targets = inputs.pop("labels")
            outputs = model(**inputs)
            loss = torch.nn.BCEWithLogitsLoss(
                pos_weight=positive_weights.to(outputs.logits.device)
            )(outputs.logits, targets)
            return (loss, outputs) if return_outputs else loss

    def metrics(evaluation):
        logits, targets = evaluation
        predictions = (1 / (1 + np.exp(-logits)) >= .5).astype(int)
        precision, recall, f1, _ = precision_recall_fscore_support(
            targets, predictions, average=None, zero_division=0
        )
        result = {
            "macro_f1": f1_score(targets, predictions, average="macro", zero_division=0),
            "micro_f1": f1_score(targets, predictions, average="micro", zero_division=0),
        }
        for index, label in enumerate(labels):
            result[f"{label}_precision"] = precision[index]
            result[f"{label}_recall"] = recall[index]
            result[f"{label}_f1"] = f1[index]
        return result

    arguments = TrainingArguments(
        output_dir=str(output / "checkpoints"), seed=args.seed,
        data_seed=args.seed, num_train_epochs=10,
        per_device_train_batch_size=8, per_device_eval_batch_size=8,
        evaluation_strategy="epoch", save_strategy="epoch",
        load_best_model_at_end=True, metric_for_best_model="macro_f1",
        greater_is_better=True, save_total_limit=2, report_to=[],
    )
    trainer = WeightedTrainer(
        model=model, args=arguments,
        train_dataset=AnnotationDataset(train),
        eval_dataset=AnnotationDataset(validation),
        compute_metrics=metrics,
        callbacks=[EarlyStoppingCallback(early_stopping_patience=2)],
    )
    trainer.train()
    test_metrics = trainer.evaluate(AnnotationDataset(test), metric_key_prefix="test")
    trainer.save_model(str(output))
    tokenizer.save_pretrained(str(output))
    metadata = {
        "base_model": "allenai/scibert_scivocab_uncased",
        "seed": args.seed, "split_unit": "paper",
        "train_rows": len(train), "validation_rows": len(validation),
        "test_rows": len(test),
        "status": "trained", "test_metrics": test_metrics,
        "loss": "class-weighted multi-label BCE",
        "early_stopping_patience": 2,
    }
    (output / "training_metadata.json").write_text(json.dumps(metadata, indent=2))
    (output / "MODEL_CARD.md").write_text(
        "# SciBERT Gap Classifier\n\nThis local run used a paper-level held-out "
        "split. Inspect `training_metadata.json` for measured metrics. Results "
        "apply only to the supplied annotation dataset and are not a general "
        "scientific-performance claim.\n"
    )
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
