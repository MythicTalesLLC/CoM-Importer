from __future__ import annotations

from dataclasses import dataclass
from typing import Any

Record = dict[str, Any]

# Canonical CoM field names and accepted normalized aliases.
COM_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "person_id": ("person_id", "id", "member_id", "employee_id"),
    "first_name": ("first_name", "firstname", "given_name", "first"),
    "last_name": ("last_name", "lastname", "family_name", "last"),
    "email": ("email", "email_address", "work_email"),
    "department": ("department", "dept", "team"),
    "start_date": ("start_date", "hire_date", "start"),
}

REQUIRED_FIELDS: tuple[str, ...] = ("person_id", "first_name", "last_name")


@dataclass(frozen=True)
class SchemaValidationResult:
    record: Record
    errors: list[str]


def _alias_to_canonical() -> dict[str, str]:
    mapping: dict[str, str] = {}
    for canonical, aliases in COM_FIELD_ALIASES.items():
        for alias in aliases:
            mapping[alias] = canonical
    return mapping


_ALIAS_MAP = _alias_to_canonical()


def map_to_com_schema(record: Record) -> Record:
    mapped: Record = {}
    extras: Record = {}

    for key, value in record.items():
        canonical = _ALIAS_MAP.get(key)
        if canonical is None:
            extras[key] = value
            continue
        mapped[canonical] = value

    if extras:
        mapped["extra"] = extras

    return mapped


def validate_com_record(record: Record) -> SchemaValidationResult:
    errors: list[str] = []
    for field in REQUIRED_FIELDS:
        value = record.get(field)
        if value in (None, ""):
            errors.append(f"missing required field: {field}")

    return SchemaValidationResult(record=record, errors=errors)
