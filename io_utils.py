"""Safe JSON, CSV, and Markdown serialization helpers."""

from __future__ import annotations

import csv
import io
import json
from dataclasses import asdict, is_dataclass
from typing import Any


def _value(obj: Any) -> Any:
    return asdict(obj) if is_dataclass(obj) else obj


def to_json(obj: Any) -> str:
    return json.dumps(_value(obj), indent=2, ensure_ascii=False, default=str)


def records_to_csv(records: list[Any]) -> str:
    values = [_value(record) for record in records]
    if not values:
        return ""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=values[0].keys())
    writer.writeheader()
    writer.writerows({key: json.dumps(value) if isinstance(value, (list, dict)) else value
                      for key, value in row.items()} for row in values)
    return output.getvalue()


def experiment_to_markdown(plan: Any) -> str:
    data = _value(plan)
    lines = ["# Minimal experiment plan", ""]
    for key, value in data.items():
        lines.extend([f"## {key.replace('_', ' ').title()}", "", str(value), ""])
    return "\n".join(lines)
