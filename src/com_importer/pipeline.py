from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import ImportConfig
from .fileio import load_records, write_jsonl
from .schema import map_to_com_schema, validate_com_record
from .transform import normalize_record

Record = dict[str, Any]


@dataclass(frozen=True)
class ImportResult:
    input_count: int
    output_count: int
    rejected_count: int
    output_path: Path


def run_import(config: ImportConfig) -> ImportResult:
    source_records = load_records(config.input_path, input_format=config.input_format)

    if config.schema_name != "com":
        raise ValueError(f"Unsupported schema profile: {config.schema_name}")

    accepted_records: list[Record] = []
    rejected_count = 0

    for raw_record in source_records:
        normalized = normalize_record(raw_record)
        if not normalized:
            rejected_count += 1
            if config.strict:
                raise ValueError("Strict mode is enabled and one or more records became empty")
            continue

        mapped = map_to_com_schema(normalized)
        validation = validate_com_record(mapped)
        if validation.errors:
            rejected_count += 1
            if config.strict:
                joined = "; ".join(validation.errors)
                raise ValueError(f"Strict mode validation failure: {joined}")
            continue

        accepted_records.append(validation.record)

    write_jsonl(config.output_path, accepted_records)

    return ImportResult(
        input_count=len(source_records),
        output_count=len(accepted_records),
        rejected_count=rejected_count,
        output_path=config.output_path,
    )
