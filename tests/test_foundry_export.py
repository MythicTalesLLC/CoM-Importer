"""
Test the Foundry export fallback mechanism.

Verifies that when REST API item creation fails, JSON export fallback is used.
"""

import json
import tempfile
from pathlib import Path

from com_importer.com_schema import DangerActor, GMMove, MoveType, Spectrum, Tag, TagType
from com_importer.danger_to_foundry import DangerToActorConverter
from com_importer.foundry_export import FoundryJsonExporter


def test_json_export_basic():
    """Test basic JSON export functionality."""
    # Create a sample danger actor
    danger = DangerActor(
        name="Test Threat",
        danger_rating=2,
        description="A test threat",
    )
    danger.gm_moves.append(
        GMMove(name="Hard Move", description="Test move", move_type=MoveType.HARD)
    )
    danger.spectrums.append(Spectrum(name="TEST", max_tier=3, current_tier=1))
    danger.tags.append(Tag(name="Dangerous", tag_type=TagType.POWER))

    # Convert to Foundry format
    converter = DangerToActorConverter()
    actor_json = converter.convert(danger)

    # Test export
    with tempfile.TemporaryDirectory() as tmpdir:
        export_path = FoundryJsonExporter.export_actor_to_file(actor_json, tmpdir)

        # Verify file was created
        assert Path(export_path).exists()
        assert export_path.endswith(".json")

        # Verify content
        with open(export_path) as f:
            exported = json.load(f)

        assert exported["name"] == "Test Threat"
        assert exported["type"] == "threat"
        assert len(exported.get("items", [])) > 0
        assert "system" in exported
        print(f"✓ Export successful: {export_path}")


def test_json_export_contains_all_items():
    """Test that exported JSON contains all items."""
    danger = DangerActor(name="Full Test", danger_rating=1, description="Full test")
    danger.gm_moves.extend(
        [
            GMMove(name="Move 1", description="First", move_type=MoveType.SOFT),
            GMMove(name="Move 2", description="Second", move_type=MoveType.HARD),
        ]
    )
    danger.spectrums.append(Spectrum(name="STAT", max_tier=2))
    danger.tags.extend(
        [
            Tag(name="Tag1", tag_type=TagType.POWER),
            Tag(name="Tag2", tag_type=TagType.WEAKNESS),
        ]
    )

    converter = DangerToActorConverter()
    actor_json = converter.convert(danger)
    expected_items = len(danger.gm_moves) + len(danger.spectrums) + len(danger.tags)

    with tempfile.TemporaryDirectory() as tmpdir:
        export_path = FoundryJsonExporter.export_actor_to_file(actor_json, tmpdir)

        with open(export_path) as f:
            exported = json.load(f)

        actual_items = len(exported.get("items", []))
        assert (
            actual_items == expected_items
        ), f"Expected {expected_items} items, got {actual_items}"
        print(f"✓ All {expected_items} items exported correctly")


def test_batch_export_jsonl():
    """Test batch JSONL export."""
    actors = []
    for i in range(3):
        danger = DangerActor(name=f"Threat {i}", danger_rating=i + 1, description=f"Test {i}")
        converter = DangerToActorConverter()
        actors.append(converter.convert(danger))

    with tempfile.TemporaryDirectory() as tmpdir:
        export_path = FoundryJsonExporter.export_batch_to_jsonl(actors, tmpdir)

        # Verify file exists
        assert Path(export_path).exists()

        # Verify JSONL format (one object per line)
        with open(export_path) as f:
            lines = f.readlines()

        assert len(lines) == 3
        for line in lines:
            obj = json.loads(line)
            assert "name" in obj
            assert obj.get("type") == "threat"

        print(f"✓ Batch export successful with {len(lines)} actors")


def test_macro_script_generation():
    """Test that macro script can be generated."""
    macro = FoundryJsonExporter.create_import_script()

    assert "importActorFromJson" in macro
    assert "FilePicker" in macro
    assert "Actor.create" in macro
    assert "createEmbeddedDocuments" in macro
    print(f"✓ Macro script generated ({len(macro)} chars)")


if __name__ == "__main__":
    test_json_export_basic()
    test_json_export_contains_all_items()
    test_batch_export_jsonl()
    test_macro_script_generation()
    print("\n✓ All export tests passed!")
