import json

import pytest

from com_importer.config import ImportConfig
from com_importer.pipeline import run_import
from com_importer.schema import (
    load_schema_definition,
    map_to_com_schema,
    map_to_schema,
    validate_com_record,
)
from com_importer.transform import normalize_record


def test_normalize_record_removes_empty_and_normalizes_keys() -> None:
    raw = {" First Name ": "  Ada ", "Last-Name": "Lovelace", "": "ignored", "Age": ""}
    out = normalize_record(raw)
    assert out == {"first_name": "Ada", "last_name": "Lovelace"}


def test_run_import_csv_to_jsonl(tmp_path) -> None:
    source = tmp_path / "people.csv"
    source.write_text(
        "Employee ID,First Name,Last Name,Role\n"
        "1001,Ada,Lovelace,Engineer\n"
        "1002,Grace,Hopper,Scientist\n",
        encoding="utf-8",
    )

    target = tmp_path / "normalized.jsonl"
    result = run_import(ImportConfig(input_path=source, output_path=target, input_format="csv"))

    assert result.input_count == 2
    assert result.output_count == 2
    assert result.rejected_count == 0

    lines = [json.loads(line) for line in target.read_text(encoding="utf-8").splitlines()]
    assert lines == [
        {
            "person_id": "1001",
            "first_name": "Ada",
            "last_name": "Lovelace",
            "extra": {"role": "Engineer"},
        },
        {
            "person_id": "1002",
            "first_name": "Grace",
            "last_name": "Hopper",
            "extra": {"role": "Scientist"},
        },
    ]


def test_map_to_com_schema_and_validation() -> None:
    mapped = map_to_com_schema(
        {
            "employee_id": "42",
            "firstname": "Alan",
            "lastname": "Turing",
            "dept": "Research",
            "favorite_color": "blue",
        }
    )

    assert mapped["person_id"] == "42"
    assert mapped["first_name"] == "Alan"
    assert mapped["last_name"] == "Turing"
    assert mapped["department"] == "Research"
    assert mapped["extra"] == {"favorite_color": "blue"}

    validation = validate_com_record(mapped)
    assert validation.errors == []


def test_strict_mode_raises_on_missing_required_fields(tmp_path) -> None:
    source = tmp_path / "missing_required.csv"
    source.write_text("First Name,Role\nAda,Engineer\n", encoding="utf-8")

    target = tmp_path / "normalized.jsonl"
    config = ImportConfig(
        input_path=source,
        output_path=target,
        input_format="csv",
        strict=True,
    )

    with pytest.raises(ValueError, match="validation failure"):
        run_import(config)


def test_load_schema_definition_from_json(tmp_path) -> None:
    field_map = tmp_path / "field_map.json"
    field_map.write_text(
        json.dumps(
            {
                "aliases": {
                    "person_id": ["staff_id"],
                    "first_name": ["given"],
                    "last_name": ["surname"],
                },
                "required_fields": ["person_id", "first_name", "last_name"],
            }
        ),
        encoding="utf-8",
    )

    schema = load_schema_definition(field_map)
    mapped = map_to_schema({"staff_id": "7", "given": "Lin", "surname": "Torvalds"}, schema)

    assert mapped == {"person_id": "7", "first_name": "Lin", "last_name": "Torvalds"}


def test_run_import_with_custom_field_map(tmp_path) -> None:
    source = tmp_path / "staff.csv"
    source.write_text("Staff ID,Given,Surname\n7,Lin,Torvalds\n", encoding="utf-8")

    field_map = tmp_path / "field_map.json"
    field_map.write_text(
        json.dumps(
            {
                "aliases": {
                    "person_id": ["staff_id"],
                    "first_name": ["given"],
                    "last_name": ["surname"],
                },
                "required_fields": ["person_id", "first_name", "last_name"],
            }
        ),
        encoding="utf-8",
    )

    target = tmp_path / "normalized.jsonl"
    result = run_import(
        ImportConfig(
            input_path=source,
            output_path=target,
            input_format="csv",
            field_map_path=field_map,
        )
    )

    assert result.output_count == 1
    payload = json.loads(target.read_text(encoding="utf-8").strip())
    assert payload["person_id"] == "7"
    assert payload["first_name"] == "Lin"
    assert payload["last_name"] == "Torvalds"
