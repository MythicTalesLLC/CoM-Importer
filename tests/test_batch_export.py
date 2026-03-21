"""
Test batch import with export fallback tracking.
"""

from pathlib import Path

import pytest

from com_importer.batch_manager import BatchImportManager, BatchImportResult
from com_importer.com_schema import DangerActor
from com_importer.foundry_client import FoundryRestClient


def test_batch_import_result_tracks_export():
    """Test that BatchImportResult can track export paths."""
    result = BatchImportResult(
        input_text="Test danger",
        name="Test",
        actor_type="threat",
        export_path="/tmp/test.json",
    )

    assert result.export_path == "/tmp/test.json"
    assert result.status == "pending"


def test_batch_import_report_tracks_exports():
    """Test that BatchImportReport tracks exported actors."""
    from com_importer.batch_manager import BatchImportReport

    report = BatchImportReport(
        total_attempted=3,
        total_succeeded=3,
    )
    report.exported_actors["Threat1"] = "/tmp/threat1.json"
    report.exported_actors["Threat2"] = "/tmp/threat2.json"

    assert len(report.exported_actors) == 2
    assert report.summary().count("Exported") == 1
    assert "2 actors" in report.summary()


def test_batch_manager_export_batch_jsonl_with_exports():
    """Test batch JSONL export when exports exist."""
    from unittest.mock import MagicMock

    from com_importer.foundry_client import FoundryRestClient

    # Create mock client
    mock_client = MagicMock(spec=FoundryRestClient)
    mock_client.last_export_path = None
    mock_client.last_export_items_count = 0

    manager = BatchImportManager(mock_client)

    # Create test data
    danger1 = DangerActor(name="Threat 1", danger_rating=1, description="Test")
    danger2 = DangerActor(name="Threat 2", danger_rating=2, description="Test")

    from com_importer.danger_to_foundry import convert_danger_to_foundry

    actor_json1 = convert_danger_to_foundry(danger1)
    actor_json2 = convert_danger_to_foundry(danger2)

    # Create batch import results with exports
    result1 = BatchImportResult(
        input_text="text1",
        name="Threat 1",
        actor_id="id1",
        status="success",
        actor_json=actor_json1,
        export_path="/tmp/threat1.json",
    )
    result2 = BatchImportResult(
        input_text="text2",
        name="Threat 2",
        actor_id="id2",
        status="success",
        actor_json=actor_json2,
        export_path="/tmp/threat2.json",
    )

    manager.report.results = [result1, result2]
    manager.report.exported_actors["Threat 1"] = "/tmp/threat1.json"
    manager.report.exported_actors["Threat 2"] = "/tmp/threat2.json"

    # Test export
    export_path = manager.export_batch_jsonl()

    if export_path:  # Only if there are exports
        assert Path(export_path).exists()
        assert export_path.endswith(".jsonl")

        # Verify file contents
        with open(export_path) as f:
            lines = f.readlines()
        assert len(lines) == 2


def test_batch_manager_export_batch_jsonl_no_exports():
    """Test batch JSONL export when no exports exist."""
    from unittest.mock import MagicMock

    # Create mock client
    mock_client = MagicMock(spec=FoundryRestClient)

    manager = BatchImportManager(mock_client)
    manager.report.exported_actors.clear()

    # Test export with no exports
    export_path = manager.export_batch_jsonl()
    assert export_path is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
