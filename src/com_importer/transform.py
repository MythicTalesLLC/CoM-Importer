from __future__ import annotations

import re
from typing import Any

Record = dict[str, Any]

_NON_WORD = re.compile(r"[^0-9a-zA-Z_]+")
_MULTI_UNDERSCORE = re.compile(r"_+")


def normalize_key(key: str) -> str:
    normalized = key.strip().lower().replace("-", " ")
    normalized = _NON_WORD.sub("_", normalized)
    normalized = _MULTI_UNDERSCORE.sub("_", normalized)
    return normalized.strip("_")


def normalize_record(record: Record) -> Record:
    normalized: Record = {}
    for key, value in record.items():
        nkey = normalize_key(str(key))
        if not nkey:
            continue
        if isinstance(value, str):
            cleaned: Any = value.strip()
        else:
            cleaned = value
        if cleaned in ("", None):
            continue
        normalized[nkey] = cleaned
    return normalized
