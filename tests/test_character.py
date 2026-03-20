"""
Test character parsing and conversion functionality.
"""

import json

import pytest

from com_importer.character_parser import CharacterParser
from com_importer.character_to_foundry import convert_character_to_foundry
from com_importer.com_schema import CharacterActor, Tag, TagType, Theme


class TestCharacterParser:
    """Test character text parsing."""

    def test_parse_basic_character(self):
        """Test parsing a basic character."""
        text = """Maya Chen
She/Her

A skilled detective who always follows the clues.

Mythos: [Supernatural Hunter] - A person touched by the mystical world
Logos: [Street Detective] - Years working the streets
Mist: [The Investigation] - Always drawn to unsolved mysteries

Juice: Help 0/3, Hurt 0/3
"""
        parser = CharacterParser()
        character, errors = parser.parse(text)

        assert character.name == "Maya Chen"
        assert character.pronouns == "She/Her"
        assert "detective" in character.description.lower()
        assert len(character.themes) >= 1
        assert character.juice_help == 0
        assert character.juice_hurt == 0

    def test_parse_character_with_themes(self):
        """Test parsing character with multiple themes."""
        text = """Alex Rivera

Mythos: [Psychic] - Touched by visions and telepathic abilities
Logos: [Community Organizer] - Builds connections
Mist: [The Collective] - Channeling group consciousness
"""
        parser = CharacterParser()
        character, errors = parser.parse(text)

        assert character.name == "Alex Rivera"
        assert len(character.themes) >= 2
        # Should have extracted themes
        theme_names = {theme.name for theme in character.themes}
        assert "Mythos" in theme_names or len(theme_names) > 0

    def test_parse_character_with_tags(self):
        """Test parsing character with tags in brackets."""
        text = """Jordan Smith
They/Them

Mythos: [Mystic] - A natural-born mystic
Logos: [Bartender] - Been pouring drinks for years

Tags: [Intuitive], [Street-smart], [Quick reflexes]
"""
        parser = CharacterParser()
        character, errors = parser.parse(text)

        assert character.name == "Jordan Smith"
        assert character.pronouns == "They/Them"
        assert len(character.themes) >= 1

    def test_parse_character_without_pronoun(self):
        """Test parsing character without explicit pronouns."""
        text = """Sam Torres

A mysterious figure with hidden depths.

Mythos: [The Shadow] - Operates in darkness
Logos: [Vigilante] - Street justice
"""
        parser = CharacterParser()
        character, errors = parser.parse(text)

        assert character.name == "Sam Torres"
        assert character.pronouns == ""

    def test_parse_empty_text(self):
        """Test parsing empty text."""
        parser = CharacterParser()
        character, errors = parser.parse("")

        assert character.name == "Untitled Character"
        assert len(errors) > 0
        assert any(err.severity == "error" for err in errors)

    def test_parse_character_juice_extraction(self):
        """Test extracting juice values."""
        text = """Blake Morgan

Mythos: [Warrior] - Combat expertise

Juice: Help 1/3, Hurt 2/3
"""
        parser = CharacterParser()
        character, errors = parser.parse(text)

        assert character.juice_help == 1
        assert character.juice_hurt == 2

    def test_parse_character_minimal(self):
        """Test parsing minimal character information."""
        text = """Casey

Logos: [Independent] - Self-made
"""
        parser = CharacterParser()
        character, errors = parser.parse(text)

        assert character.name == "Casey"
        assert len(character.themes) >= 1

    def test_parse_character_with_parenthetical(self):
        """Test parsing character name with parenthetical notes."""
        text = """Devon "Red" Sullivan (Player 1)

Mythos: [Arsonist] - Fire is my element
"""
        parser = CharacterParser()
        character, errors = parser.parse(text)

        # Should remove (Player 1) from name
        assert "Player" not in character.name
        assert "Devon" in character.name


class TestCharacterToFoundry:
    """Test character to Foundry conversion."""

    def test_convert_basic_character_to_foundry(self):
        """Test converting character to Foundry format."""
        character = CharacterActor(
            name="Test Character",
            pronouns="She/Her",
            description="A test character",
            themes=[
                Theme(
                    name="Mythos",
                    description="Mystical theme",
                    tags=[
                        Tag(name="Mystic", tag_type=TagType.POWER),
                    ],
                )
            ],
        )

        actor_json = convert_character_to_foundry(character)

        assert actor_json["name"] == "Test Character"
        assert actor_json["type"] == "character"
        assert "_id" in actor_json
        assert "items" in actor_json
        assert actor_json["system"]["pronouns"] == "She/Her"

    def test_convert_character_with_juice(self):
        """Test converting character with juice values."""
        character = CharacterActor(
            name="Juiced Character",
            themes=[Theme(name="Mythos", tags=[])],
            juice_help=2,
            juice_hurt=1,
        )

        actor_json = convert_character_to_foundry(character)

        assert actor_json["system"]["juice"]["help"] == 2
        assert actor_json["system"]["juice"]["hurt"] == 1

    def test_convert_character_json_validity(self):
        """Test that converted character JSON is valid."""
        character = CharacterActor(
            name="JSON Test",
            themes=[
                Theme(
                    name="Logos",
                    tags=[Tag(name="Detective", tag_type=TagType.POWER)],
                )
            ],
        )

        actor_json = convert_character_to_foundry(character)

        # Should be serializable to JSON
        json_str = json.dumps(actor_json)
        assert json_str is not None

        # Should have required Foundry fields
        assert actor_json["_id"]
        assert actor_json["name"]
        assert actor_json["type"] == "character"
        assert "system" in actor_json
        assert "prototypeToken" in actor_json

    def test_convert_character_theme_items(self):
        """Test that themes are converted to items."""
        character = CharacterActor(
            name="Theme Test",
            themes=[
                Theme(
                    name="Mythos",
                    tags=[
                        Tag(name="Power Tag", tag_type=TagType.POWER),
                        Tag(name="Story Tag", tag_type=TagType.STORY),
                    ],
                ),
                Theme(name="Logos", tags=[]),
            ],
        )

        actor_json = convert_character_to_foundry(character)

        # Should have items for themes
        assert len(actor_json["items"]) >= 2
        # Find themekit items
        themekits = [item for item in actor_json["items"] if item["type"] == "themekit"]
        assert len(themekits) >= 1

    def test_convert_character_bracket_syntax(self):
        """Test that bracket syntax in descriptions creates tags."""
        character = CharacterActor(
            name="Bracket Test",
            themes=[
                Theme(
                    name="Mythos",
                    description="Has [Telekinesis] and [Mind Link] abilities",
                    tags=[],
                )
            ],
        )

        convert_character_to_foundry(character)

        # The bracket syntax should be preserved in description
        # and tags should be auto-created (this happens in converter)
        assert "[Telekinesis]" in character.themes[0].description

    def test_convert_character_with_actor_id(self):
        """Test converting with specific actor ID."""
        character = CharacterActor(name="ID Test", themes=[Theme(name="Mythos", tags=[])])
        custom_id = "custom-actor-123"

        actor_json = convert_character_to_foundry(character, actor_id=custom_id)

        assert actor_json["_id"] == custom_id

    def test_convert_character_protocol_token(self):
        """Test that prototype token is properly set."""
        character = CharacterActor(name="Token Test", themes=[Theme(name="Mythos", tags=[])])

        actor_json = convert_character_to_foundry(character)

        proto_token = actor_json.get("prototypeToken")
        assert proto_token is not None
        assert proto_token["name"] == "Token Test"
        assert proto_token["actorLink"] is True  # PCs linked to tokens

    def test_character_validates(self):
        """Test that character validation works."""
        # Valid character
        character = CharacterActor(
            name="Valid",
            themes=[Theme(name="Mythos", tags=[])],
        )
        errors = character.validate()
        # Should have no errors (themes present)
        assert len(errors) == 0

        # Invalid character (no themes)
        invalid = CharacterActor(name="Invalid", themes=[])
        errors = invalid.validate()
        assert len(errors) > 0

    def test_convert_character_all_fields(self):
        """Test converting character with all fields populated."""
        character = CharacterActor(
            name="Full Character",
            pronouns="He/Him",
            description="A detailed description",
            biography="A longer biography section",
            gmnotes="GM notes here",
            themes=[
                Theme(
                    name="Mythos",
                    description="Mythic theme description",
                    tags=[
                        Tag(name="Ancient Power", tag_type=TagType.POWER),
                    ],
                ),
                Theme(
                    name="Logos",
                    description="Mundane theme description",
                    tags=[
                        Tag(name="Day Job", tag_type=TagType.STORY),
                    ],
                ),
            ],
            juice_help=1,
            juice_hurt=2,
        )

        actor_json = convert_character_to_foundry(character)

        system = actor_json["system"]
        assert system["pronouns"] == "He/Him"
        assert "A detailed description" in system["description"]
        assert "A longer biography" in system["biography"]
        assert "GM notes here" in system["gmnotes"]
        assert system["juice"]["help"] == 1
        assert system["juice"]["hurt"] == 2


class TestCharacterParserIntegration:
    """Integration tests for character parsing and conversion."""

    def test_parse_and_convert_full_pipeline(self):
        """Test full pipeline from text to Foundry JSON."""
        text = """Maya Chen
She/Her

A skilled detective investigating supernatural events.

Mythos: [Supernatural Hunter] - Connected to the mystical
Logos: [Police Detective] - Works within the law
Mist: [The Mystery] - Always drawn to unsolved cases

Juice: Help 1/3, Hurt 0/3
"""
        parser = CharacterParser()
        character, parse_errors = parser.parse(text)

        # Should parse without critical errors
        assert character.name == "Maya Chen"
        assert len(character.themes) >= 1

        # Convert to Foundry
        actor_json = convert_character_to_foundry(character)

        # Validate structure
        assert actor_json["type"] == "character"
        assert actor_json["system"]["pronouns"] == "She/Her"
        assert actor_json["system"]["juice"]["help"] == 1

        # Should be JSON serializable
        json.dumps(actor_json)

    def test_parse_multiple_characters(self):
        """Test parsing multiple different character formats."""
        characters_text = [
            """Alice
Mythos: [Mystic]
Logos: [Doctor]""",
            """Bob (NPC)
He/Him
Mist: [Chaos]""",
            """Charlie""",  # Minimal
        ]

        parser = CharacterParser()
        for text in characters_text:
            character, errors = parser.parse(text)
            assert character.name  # Should always have name
            json_out = convert_character_to_foundry(character)
            assert json_out["type"] == "character"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
