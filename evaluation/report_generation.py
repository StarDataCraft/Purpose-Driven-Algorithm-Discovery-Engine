"""Stable JSON/Markdown evaluation exports."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from evaluation.schemas import EvaluationReport


def report_json(report: EvaluationReport) -> str:
    return json.dumps(asdict(report), indent=2, sort_keys=True, default=str)


def report_markdown(report: EvaluationReport) -> str:
    metrics = "\n".join(
        f"- {key}: {value}" for key, value in report.retrieval_metrics.items()
    )
    funnel = "\n".join(
        f"- {key}: {value}" for key, value in asdict(report.funnel).items()
    )
    errors = "\n".join(
        f"- {key}: {value}" for key, value in report.error_counts.items()
    ) or "- No reviewed errors recorded."
    return f"""# Quality evaluation: {report.task_id}

> Automated quality metrics are meaningful only against reviewed annotations.
> The deterministic offline labels are synthetic CI fixtures, not scientific ground truth.

## Purpose

Benchmark version: `{report.benchmark_version}`

## Run provenance

```json
{json.dumps(report.run_provenance, indent=2, sort_keys=True, default=str)}
```

## Query set and contribution

{chr(10).join(f"- `{item.query}` — {item.stage}; unique={item.unique_papers_contributed}; relevant={item.relevant_papers_contributed}; labels={item.quality_labels}" for item in report.query_contributions)}

## Retrieval metrics

{metrics}

## Top retrieved papers and relevance labels

```json
{json.dumps(report.run_provenance.get("top_retrieved_papers", []), indent=2)}
```

## Gap extraction results

```json
{json.dumps([asdict(item) for item in report.gap_audits], indent=2)}
```

## Coverage-gap audit

```json
{json.dumps([asdict(item) for item in report.coverage_audits], indent=2)}
```

## Assumption-mismatch audit

```json
{json.dumps([asdict(item) for item in report.mismatch_audits], indent=2)}
```

## Algorithm-binding audit

```json
{json.dumps([asdict(item) for item in report.binding_audits], indent=2)}
```

## Known-solution audit

```json
{json.dumps([asdict(item) for item in report.known_solution_audits], indent=2)}
```

## External-domain search quality

```json
{json.dumps([asdict(item) for item in report.external_query_audits], indent=2)}
```

## Mechanism quality

```json
{json.dumps([asdict(item) for item in report.mechanism_audits], indent=2)}
```

## Alignment quality

```json
{json.dumps([asdict(item) for item in report.alignment_audits], indent=2)}
```

## Candidate rubric

```json
{json.dumps([asdict(item) for item in report.candidate_audits], indent=2)}
```

## Stage funnel

{funnel}

## Dominant errors

{errors}

Dominant bottleneck: **{report.dominant_bottleneck}**

## Targeted repairs made

{chr(10).join(f"- {item}" for item in report.before_after.get("repairs", [])) or "- None."}

## Before/after comparison

```json
{json.dumps(report.before_after, indent=2, sort_keys=True, default=str)}
```

## Remaining limitations

{chr(10).join(f"- {item}" for item in report.limitations)}
"""


def write_report(report: EvaluationReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        report_markdown(report) if path.suffix == ".md" else report_json(report)
    )
