from __future__ import annotations

import argparse
from pathlib import Path

from .config import ImportConfig
from .pipeline import run_import


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Normalize CoM data into JSONL")
    parser.add_argument("-i", "--input", required=True, type=Path, help="Input file path")
    parser.add_argument("-o", "--output", required=True, type=Path, help="Output JSONL path")
    parser.add_argument(
        "--format",
        dest="input_format",
        choices=["csv", "json", "jsonl"],
        default=None,
        help="Optional explicit input format",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail if any record is empty after normalization",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    config = ImportConfig(
        input_path=args.input,
        output_path=args.output,
        input_format=args.input_format,
        strict=args.strict,
    )
    result = run_import(config)
    summary = (
        f"Imported {result.input_count} records -> "
        f"{result.output_count} written to {result.output_path}"
    )
    print(summary)
    return 0
