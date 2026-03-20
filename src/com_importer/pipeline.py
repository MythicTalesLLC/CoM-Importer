from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import ImportConfig
from .fileio import load_records, write_jsonl
from .transform import normalize_record


@dataclass(frozen=True)
class ImportResult:
    input_count: int
    output_count: int
    output_path: Path


def run_import(config: ImportConfig) -> ImportResult:
    source_records = load_records(config.input_path, input_format=config.input_format)

    normalized_records = [normalize_record(record) for record in source_records]
    if config.strict and any(not record for record in normalized_records):
        raise ValueError("Strict mode is enabled and one or more records became empty")

    normalized_records = [record for record in normalized_records if record]
    write_jsonl(config.output_path, normalized_records)

    return ImportResult(
        input_count=len(source_records),
        output_count=len(normalized_records),
        output_path=config.output_path,
    )
