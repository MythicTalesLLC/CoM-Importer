"""
Test the history persistence functionality.
"""

import json
import tempfile
from datetime import datetime, timedelta

from com_importer.history_manager import HistoryEntry, HistoryManager


def test_history_persistence():
    """Test history manager persistence."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    # Create manager
    manager = HistoryManager(db_path)

    # Create test entries
    entry1 = HistoryEntry(
        actor_id="actor123",
        danger_name="Zeus",
        danger_rating="3",
        actor_json={"name": "Zeus", "type": "threat"},
        foundry_url="https://example.com",
        source="text",
        status="success",
    )

    entry2 = HistoryEntry(
        actor_id="actor456",
        danger_name="Hades",
        danger_rating="4",
        actor_json={"name": "Hades", "type": "threat"},
        source="image",
        status="success",
        created_at=datetime.now() - timedelta(days=1),
    )

    entry3 = HistoryEntry(
        actor_id="actor789",
        danger_name="Fail Danger",
        actor_json={},
        source="batch",
        status="failed",
        error_message="Connection timeout",
    )

    # Add entries
    id1 = manager.add_entry(entry1)
    id2 = manager.add_entry(entry2)
    id3 = manager.add_entry(entry3)

    print(f"✓ Added 3 entries (IDs: {id1}, {id2}, {id3})")

    # Test retrieval
    retrieved = manager.get_entry("actor123")
    assert retrieved is not None
    assert retrieved.danger_name == "Zeus"
    print("✓ Retrieved single entry")

    # Test recent
    recent = manager.get_recent(limit=10)
    assert len(recent) == 3
    print(f"✓ Retrieved {len(recent)} recent entries")

    # Test by status
    success_entries = manager.get_by_status("success")
    assert len(success_entries) == 2
    print(f"✓ Found {len(success_entries)} successful imports")

    failed_entries = manager.get_by_status("failed")
    assert len(failed_entries) == 1
    print(f"✓ Found {len(failed_entries)} failed imports")

    # Test by source
    text_entries = manager.get_by_source("text")
    assert len(text_entries) == 1
    print(f"✓ Found {len(text_entries)} text imports")

    # Test statistics
    stats = manager.get_statistics()
    assert stats["total"] == 3
    assert stats["success"] == 2
    assert stats["failed"] == 1
    print(f"✓ Statistics: {stats}")

    # Test export
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        export_path = f.name

    manager.export_json(export_path)
    with open(export_path) as f:
        exported = json.load(f)
    assert exported["entry_count"] == 3
    print(f"✓ Exported {exported['entry_count']} entries to JSON")

    # Test deletion
    manager.delete_entry("actor789")
    remaining = manager.get_all()
    assert len(remaining) == 2
    print("✓ Deleted entry, 2 remain")

    # Test clear
    cleared_count = manager.clear_all()
    assert cleared_count == 2
    print(f"✓ Cleared {cleared_count} entries")

    print("\n✅ All history tests passed!")


if __name__ == "__main__":
    test_history_persistence()
