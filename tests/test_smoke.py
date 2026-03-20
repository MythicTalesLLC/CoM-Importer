import json

from com_importer.config import ImportConfig
from com_importer.pipeline import run_import
from com_importer.transform import normalize_record


def test_normalize_record_removes_empty_and_normalizes_keys() -> None:
    raw = {" First Name ": "  Ada ", "Last-Name": "Lovelace", "": "ignored", "Age": ""}
    out = normalize_record(raw)
    assert out == {"first_name": "Ada", "last_name": "Lovelace"}


def test_run_import_csv_to_jsonl(tmp_path) -> None:
    source = tmp_path / "people.csv"
    source.write_text("Name,Role\nAda,Engineer\nGrace,Scientist\n", encoding="utf-8")

    target = tmp_path / "normalized.jsonl"
    result = run_import(ImportConfig(input_path=source, output_path=target, input_format="csv"))

    assert result.input_count == 2
    assert result.output_count == 2

    lines = [json.loads(line) for line in target.read_text(encoding="utf-8").splitlines()]
    assert lines == [
        {"name": "Ada", "role": "Engineer"},
        {"name": "Grace", "role": "Scientist"},
    ]
