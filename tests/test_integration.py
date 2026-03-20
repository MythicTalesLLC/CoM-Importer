"""
Integration tests for the CoM Importer core pipeline.

Tests the full path: text input -> parsing -> schema validation -> Foundry format.
"""

import json

import pytest

from com_importer.com_schema import DangerActor, GMMove, MoveType, Spectrum, Tag
from com_importer.danger_parser import DangerParser
from com_importer.danger_to_foundry import convert_danger_to_foundry
from com_importer.danger_transform import normalize_danger_text


class TestDangerParsing:
    """Test danger text parsing."""

    def test_parse_simple_danger(self):
        """Test parsing a basic danger entry."""
        text = """
        Zeus - Danger Rating 3

        A lecherous salesman who deals in luxury electric cars.

        Mythos: Zeus
        Logos: Electric Car Salesman

        Spectrum:
        Hurt: 0/4

        Hard Moves:
        - Lightning Strike: Deals damage to target
        - Remote Control: Controls nearby vehicles

        Soft Moves:
        - Make a dramatic entrance
        - Demand a price from the player
        """

        parser = DangerParser()
        danger, errors = parser.parse(text)

        assert danger.name == "Zeus - Danger Rating 3"
        assert danger.mythos == "Zeus"
        assert danger.logos == "Electric Car Salesman"
        assert len(danger.spectrums) > 0
        assert len(danger.gm_moves) > 0

    def test_parse_text_normalization(self):
        """Test that text normalization works."""
        text = "  Zeus\n\n\nDanger Rating 3  "
        normalized = normalize_danger_text(text)

        assert normalized.startswith("zeus")  # normalize_danger_text lowercases
        assert "danger rating 3" in normalized.lower()

    def test_danger_validation(self):
        """Test danger validation catches missing fields."""
        danger = DangerActor(name="")
        errors = danger.validate()

        assert len(errors) > 0
        assert any("name" in error.lower() for error in errors)

    def test_danger_with_all_fields(self):
        """Test parsing danger with comprehensive fields."""
        danger = DangerActor(
            name="Test Danger",
            mythos="Mythic",
            logos="Mundane",
            description="A test danger",
            gm_moves=[
                GMMove(
                    name="Hard Move",
                    description="Do something",
                    move_type=MoveType.HARD,
                )
            ],
            spectrums=[Spectrum(name="Hurt", max_tier=4)],
            tags=[Tag(name="Powerful")],
        )

        errors = danger.validate()
        assert len(errors) == 0


class TestFoundryConversion:
    """Test conversion to Foundry format."""

    def test_danger_to_foundry_format(self):
        """Test converting danger to Foundry actor JSON."""
        danger = DangerActor(
            name="Zeus",
            mythos="Zeus",
            logos="Car Salesman",
            description="A lecherous god",
            gm_moves=[
                GMMove(
                    name="Strike with Lightning",
                    description="Damage with electricity [fried-3]",
                    move_type=MoveType.HARD,
                )
            ],
            spectrums=[Spectrum(name="Hurt", max_tier=4, current_tier=0)],
        )

        actor_json = convert_danger_to_foundry(danger)

        # Verify structure
        assert actor_json["name"] == "Zeus"
        assert actor_json["type"] == "threat"
        assert "system" in actor_json
        assert actor_json["system"]["mythos"] == "Zeus"
        assert actor_json["system"]["logos"] == "Car Salesman"

        # Verify items
        assert "items" in actor_json
        assert len(actor_json["items"]) > 0

        # Check for GM move
        gm_moves = [item for item in actor_json["items"] if item.get("type") == "gmmove"]
        assert len(gm_moves) > 0

    def test_bracket_syntax_auto_creation(self):
        """Test that bracket syntax creates tags/statuses."""
        danger = DangerActor(
            name="Danger",
            gm_moves=[
                GMMove(
                    name="Move",
                    description="Something [powerful] happens and [fried-3]",
                    move_type=MoveType.HARD,
                )
            ],
        )

        actor_json = convert_danger_to_foundry(danger)

        # Should have auto-created status and tag
        tags = [item for item in actor_json["items"] if item.get("type") == "tag"]
        statuses = [item for item in actor_json["items"] if item.get("type") == "status"]

        assert len(tags) > 0 or len(statuses) > 0

    def test_foundry_json_validity(self):
        """Test that generated Foundry JSON is valid."""
        danger = DangerActor(
            name="Test",
            description="Test description",
            gm_moves=[GMMove(name="Move", description="Do it", move_type=MoveType.SOFT)],
        )

        actor_json = convert_danger_to_foundry(danger)

        # Should be JSON serializable
        json_str = json.dumps(actor_json)
        parsed = json.loads(json_str)

        assert parsed["type"] == "threat"

    def test_spectrum_formatting(self):
        """Test that spectrums are properly formatted."""
        danger = DangerActor(
            name="Test",
            description="Test",
            spectrums=[
                Spectrum(name="Hurt", max_tier=4, current_tier=2, pips=1),
                Spectrum(name="Caught", max_tier=2, current_tier=0, pips=0),
            ],
            gm_moves=[GMMove(name="M", description="D", move_type=MoveType.SOFT)],
        )

        actor_json = convert_danger_to_foundry(danger)

        spectrums = [item for item in actor_json["items"] if item.get("type") == "spectrum"]
        assert len(spectrums) == 2
        assert spectrums[0]["name"] == "Hurt"
        assert spectrums[0]["system"]["tier"] == 2


class TestEndToEndPipeline:
    """Test the complete pipeline."""

    def test_full_pipeline_text_to_foundry(self):
        """Test complete pipeline from text to Foundry format."""
        text = """
        Zeus - Danger Rating 3

        A powerful entity dealing in luxury items.

        Spectrum:
        Hurt: 0/4
        Outsmarted: 0/3

        Hard Moves:
        - Strike with Lightning: Deal [fried-3] damage
        - Command Subject: Force [compliance-2]
        """

        # Step 1: Normalize
        normalized = normalize_danger_text(text)
        assert normalized

        # Step 2: Parse
        parser = DangerParser()
        danger, errors = parser.parse(normalized)
        assert danger.name

        # Step 3: Validate (warnings are OK)
        danger.validate()

        # Step 4: Convert to Foundry
        actor_json = convert_danger_to_foundry(danger)
        assert actor_json["type"] == "threat"

        # Step 5: Verify JSON is serializable
        json_str = json.dumps(actor_json)
        assert len(json_str) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
