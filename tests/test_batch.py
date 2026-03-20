"""
Test batch import functionality.
"""

import json
import tempfile
from pathlib import Path

import pytest

from com_importer.batch_manager import (
    BatchImportManager,
    BatchImportParser,
    BatchImportReport,
)


class TestBatchImportParser:
    """Test batch import file parsing."""

    def test_parse_text_blocks(self):
        """Test parsing text blocks separated by delimiter."""
        text = "Danger 1 text\n---\nDanger 2 text\n---\nDanger 3 text"
        blocks = BatchImportParser.parse_text_blocks(text)

        assert len(blocks) == 3
        assert blocks[0] == "Danger 1 text"
        assert blocks[1] == "Danger 2 text"
        assert blocks[2] == "Danger 3 text"

    def test_parse_jsonl(self):
        """Test parsing JSONL file."""
        data = [
            {"text": "Danger 1 description"},
            {"text": "Danger 2 description"},
            {"description": "Danger 3 description"},
        ]

        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".jsonl",
            delete=False,
            encoding="utf-8",
        ) as f:
            for entry in data:
                f.write(json.dumps(entry) + "\n")
            temp_path = f.name

        try:
            blocks = BatchImportParser.parse_jsonl(temp_path)
            assert len(blocks) == 3
            assert "Danger 1" in blocks[0]
            assert "Danger 3" in blocks[2]
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_parse_csv(self):
        """Test parsing CSV file."""
        import csv

        data = [
            {"text": "Danger 1", "rating": "3"},
            {"text": "Danger 2", "rating": "4"},
        ]

        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".csv",
            delete=False,
            newline="",
            encoding="utf-8",
        ) as f:
            writer = csv.DictWriter(f, fieldnames=["text", "rating"])
            writer.writeheader()
            writer.writerows(data)
            temp_path = f.name

        try:
            blocks = BatchImportParser.parse_csv(temp_path, text_column="text")
            assert len(blocks) == 2
            assert "Danger 1" in blocks[0]
            assert "Danger 2" in blocks[1]
        finally:
            Path(temp_path).unlink(missing_ok=True)


class TestBatchImportReport:
    """Test batch import reporting."""

    def test_report_summary(self):
        """Test report summary generation."""
        report = BatchImportReport(
            total_attempted=10,
            total_succeeded=8,
            total_failed=2,
        )

        assert report.success_rate == 80.0
        summary = report.summary()
        assert "10" in summary
        assert "Success Rate: 80.0" in summary

    def test_empty_report(self):
        """Test empty report."""
        report = BatchImportReport()
        assert report.success_rate == 0.0
        assert report.total_attempted == 0


class TestBatchImportManager:
    """Test batch import manager."""

    def test_manager_initialization(self):
        """Test manager can be initialized."""
        # Create a mock client
        client = MockFoundryClient()
        manager = BatchImportManager(client)

        assert manager.foundry_client == client
        assert len(manager.created_actor_ids) == 0

    def test_import_single_text(self):
        """Test importing a single text."""
        client = MockFoundryClient()
        manager = BatchImportManager(client)

        text = "Zeus - Danger Rating 3\nA powerful entity\nSpectrum: Hurt 0/4"
        result = manager._import_single_text(text)

        # Should parse successfully
        assert result.status == "success"
        assert result.danger_name == "Zeus - Danger Rating 3"
        assert result.actor_id is not None
        assert result.actor_json is not None

    def test_import_invalid_text(self):
        """Test importing invalid text."""
        client = MockFoundryClient()
        manager = BatchImportManager(client)

        text = ""  # Empty text
        result = manager._import_single_text(text)

        assert result.status == "failed"
        assert result.error_message is not None


class MockFoundryClient:
    """Mock Foundry client for testing."""

    def __init__(self):
        self.created_actors = []

    def create_actor(self, actor_data):
        """Mock create_actor."""
        import uuid

        actor_id = str(uuid.uuid4())
        self.created_actors.append((actor_id, actor_data))
        return actor_id

    def test_connection(self):
        """Mock test_connection."""
        return (True, "Mock connection successful")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
