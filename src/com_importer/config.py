from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ImportConfig:
    input_path: Path
    output_path: Path
    input_format: str | None = None
    schema_name: str = "com"
    strict: bool = False
