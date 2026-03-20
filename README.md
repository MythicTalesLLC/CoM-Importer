# CoM_Importer

A Python importer scaffold for normalizing CoM data from CSV, JSON, or JSONL and
writing normalized JSONL output.

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
com-importer --help
```

## Example

```bash
com-importer \
	--input sample.csv \
	--output normalized.jsonl \
	--format csv
```

## Dev Workflow

```bash
source .venv/bin/activate
pre-commit install
pre-commit run --all-files
pytest
```
