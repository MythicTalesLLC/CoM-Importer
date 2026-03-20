from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

Record = dict[str, Any]


def _detect_format(path: Path, input_format: str | None) -> str:
    if input_format:
        return input_format

    suffix = path.suffix.lower()
    if suffix == ".csv":
        return "csv"
    if suffix == ".json":
        return "json"
    if suffix == ".jsonl":
        return "jsonl"
    raise ValueError(f"Unsupported input format for file: {path}")


def load_records(path: Path, input_format: str | None = None) -> list[Record]:
    fmt = _detect_format(path, input_format)

    if fmt == "csv":
        with path.open("r", encoding="utf-8", newline="") as handle:
            return [dict(row) for row in csv.DictReader(handle)]

    if fmt == "json":
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if isinstance(payload, list):
            return [dict(item) for item in payload if isinstance(item, dict)]
        if isinstance(payload, dict):
            return [dict(payload)]
        raise ValueError("JSON input must be an object or array of objects")

    if fmt == "jsonl":
        records: list[Record] = []
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                stripped = line.strip()
                if not stripped:
                    continue
                payload = json.loads(stripped)
                if not isinstance(payload, dict):
                    raise ValueError("Each JSONL line must be an object")
                records.append(dict(payload))
        return records

    raise ValueError(f"Unsupported input format: {fmt}")


def write_jsonl(path: Path, records: list[Record]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
