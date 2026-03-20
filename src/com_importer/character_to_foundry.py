"""
Convert parsed character actors into Foundry-compatible JSON format.

Handles bracket syntax parsing, tag/status auto-creation, and schema compliance.
"""

from __future__ import annotations

import re
import uuid
from typing import Any

from .com_schema import (
    CharacterActor,
    Tag,
    TagType,
)


class CharacterToActorConverter:
    """Converts CharacterActor objects to Foundry actor JSON."""

    # Pattern for [tag-name] syntax in descriptions
    BRACKET_PATTERN = r"\[([^\]]+)\]"

    def __init__(self) -> None:
        """Initialize converter."""
        self.created_tags: set[str] = set()

    def convert(self, character: CharacterActor, actor_id: str | None = None) -> dict[str, Any]:
        """
        Convert a CharacterActor to Foundry actor JSON.

        Args:
            character: CharacterActor to convert
            actor_id: Optional actor ID; generated if not provided

        Returns:
            Foundry actor JSON object
        """
        if actor_id is None:
            actor_id = str(uuid.uuid4())

        # Parse bracket syntax in theme descriptions to auto-create tags
        self._parse_bracket_syntax(character)

        # Apply auto-created items to character's themes
        self._apply_auto_created_items(character)

        # Convert to Foundry format using CharacterActor's built-in method
        actor_json = character.to_foundry_actor(actor_id)

        # Enhance with additional validations and processing
        self._enhance_actor(actor_json)

        return actor_json

    def _parse_bracket_syntax(self, character: CharacterActor) -> None:
        """
        Parse [tag] syntax in theme descriptions.

        Extracts referenced tags for auto-creation.
        """
        for theme in character.themes:
            # Find all bracketed references in theme description
            for match in re.finditer(self.BRACKET_PATTERN, theme.description):
                bracket_content = match.group(1).strip()

                if bracket_content not in self.created_tags:
                    self.created_tags.add(bracket_content)
                    tag_type = self._infer_tag_type(bracket_content)
                    tag = Tag(
                        name=bracket_content,
                        tag_type=tag_type,
                    )
                    theme.tags.append(tag)

            # Also parse tags in existing theme tags
            for tag in theme.tags:
                # Check if tag name contains bracket syntax (unlikely but handle it)
                for match in re.finditer(self.BRACKET_PATTERN, tag.description):
                    bracket_content = match.group(1).strip()
                    if bracket_content not in self.created_tags:
                        self.created_tags.add(bracket_content)

    def _infer_tag_type(self, tag_name: str) -> TagType:
        """Infer tag type from tag name."""
        tag_lower = tag_name.lower()

        if any(
            word in tag_lower
            for word in (
                "power",
                "ability",
                "strength",
                "force",
                "skill",
                "talent",
            )
        ):
            return TagType.POWER
        if any(word in tag_lower for word in ("weak", "vulnerable", "fear", "scared", "burden")):
            return TagType.WEAKNESS
        if any(
            word in tag_lower
            for word in ("gun", "weapon", "tool", "gear", "equipment", "car", "device")
        ):
            return TagType.LOADOUT
        if any(
            word in tag_lower
            for word in (
                "known",
                "love",
                "hate",
                "friend",
                "enemy",
                "ally",
                "crew",
                "partner",
            )
        ):
            return TagType.RELATIONSHIP

        return TagType.STORY

    def _apply_auto_created_items(self, character: CharacterActor) -> None:
        """
        Apply auto-created tags to character's themes.

        Ensures no duplicates are added.
        """
        # Collect existing tag names across all themes
        existing_tag_names = set()
        for theme in character.themes:
            for tag in theme.tags:
                existing_tag_names.add(tag.name.lower())

        # Filter to avoid duplicates
        self.created_tags = {
            tag for tag in self.created_tags if tag.lower() not in existing_tag_names
        }

    def _enhance_actor(self, actor_json: dict[str, Any]) -> None:
        """
        Apply enhancements and validations to the actor JSON.

        Args:
            actor_json: Foundry actor JSON to enhance
        """
        system = actor_json.get("system", {})

        # Ensure required fields have defaults
        if "locked" not in system:
            system["locked"] = False
        if not system.get("version"):
            system["version"] = "3.0.0"

        # Initialize juice if not present
        if "juice" not in system:
            system["juice"] = {"help": 0, "hurt": 0}

        # Ensure items is a list
        if "items" not in actor_json:
            actor_json["items"] = []

        # Assign IDs to items that don't have them
        for item in actor_json.get("items", []):
            if "_id" not in item:
                item["_id"] = str(uuid.uuid4())

            # Assign IDs to nested items in themes
            if item.get("type") == "themekit":
                for nested_item in item.get("items", []):
                    if "_id" not in nested_item:
                        nested_item["_id"] = str(uuid.uuid4())

        # Clean up HTML in fields
        for field in ("biography", "description", "gmnotes"):
            if field in system and system[field]:
                system[field] = self._clean_html_field(system[field])

    def _clean_html_field(self, text: str) -> str:
        """Clean potential HTML in text fields."""
        if not text:
            return text

        # Remove any control characters
        text = "".join(char for char in text if ord(char) >= 32 or char in "\n\t")

        return text.strip()


def convert_character_to_foundry(
    character: CharacterActor,
    actor_id: str | None = None,
) -> dict[str, Any]:
    """
    Convenience function to convert a character to Foundry format.

    Args:
        character: CharacterActor to convert
        actor_id: Optional actor ID

    Returns:
        Foundry actor JSON
    """
    converter = CharacterToActorConverter()
    return converter.convert(character, actor_id)
