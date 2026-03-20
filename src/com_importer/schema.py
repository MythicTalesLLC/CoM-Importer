from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

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
class SchemaDefinition:
    aliases: dict[str, tuple[str, ...]]
    required_fields: tuple[str, ...]


@dataclass(frozen=True)
class SchemaValidationResult:
    record: Record
    errors: list[str]


def default_schema_definition() -> SchemaDefinition:
    return SchemaDefinition(aliases=COM_FIELD_ALIASES, required_fields=REQUIRED_FIELDS)


def load_schema_definition(path: Path) -> SchemaDefinition:
    raw = _load_data(path)

    aliases_raw = raw.get("aliases")
    if not isinstance(aliases_raw, dict):
        raise ValueError("Field-map must include an 'aliases' object")

    required_raw = raw.get("required_fields", [])
    if not isinstance(required_raw, list) or not all(
        isinstance(item, str) for item in required_raw
    ):
        raise ValueError("'required_fields' must be a list of strings")

    aliases: dict[str, tuple[str, ...]] = {}
    for canonical, alias_values in aliases_raw.items():
        if not isinstance(canonical, str):
            raise ValueError("Canonical alias keys must be strings")
        if not isinstance(alias_values, list) or not all(
            isinstance(item, str) for item in alias_values
        ):
            raise ValueError(f"Aliases for '{canonical}' must be a list of strings")
        aliases[canonical] = tuple(alias_values)

    required_fields = tuple(required_raw)
    return SchemaDefinition(aliases=aliases, required_fields=required_fields)


def _load_data(path: Path) -> dict[str, Any]:
    suffix = path.suffix.lower()
    text = path.read_text(encoding="utf-8")

    if suffix == ".json":
        payload = json.loads(text)
    elif suffix in {".yml", ".yaml"}:
        payload = yaml.safe_load(text)
    else:
        raise ValueError(f"Unsupported field-map file format: {path}")

    if not isinstance(payload, dict):
        raise ValueError("Field-map root must be an object")
    return payload


def alias_to_canonical(aliases: dict[str, tuple[str, ...]]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for canonical, alias_values in aliases.items():
        for alias in alias_values:
            mapping[alias] = canonical
    return mapping


def map_to_schema(record: Record, schema: SchemaDefinition) -> Record:
    alias_map = alias_to_canonical(schema.aliases)
    mapped: Record = {}
    extras: Record = {}

    for key, value in record.items():
        canonical = alias_map.get(key)
        if canonical is None:
            extras[key] = value
            continue
        mapped[canonical] = value

    if extras:
        mapped["extra"] = extras

    return mapped


def validate_record(record: Record, required_fields: tuple[str, ...]) -> SchemaValidationResult:
    errors: list[str] = []
    for field in required_fields:
        value = record.get(field)
        if value in (None, ""):
            errors.append(f"missing required field: {field}")

    return SchemaValidationResult(record=record, errors=errors)


def map_to_com_schema(record: Record) -> Record:
    return map_to_schema(record, default_schema_definition())


def validate_com_record(record: Record) -> SchemaValidationResult:
    return validate_record(record, REQUIRED_FIELDS)
