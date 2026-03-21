"""
Convert parsed danger actors into Foundry-compatible JSON format.

Handles bracket syntax parsing, tag/status auto-creation, and schema compliance.
"""

from __future__ import annotations

import re
import uuid
from typing import Any

from .com_schema import (
    DangerActor,
    DangerStatus,
    StatusCategory,
    Tag,
    TagType,
)


class DangerToActorConverter:
    """Converts DangerActor objects to Foundry actor JSON."""

    # Pattern for [tag-name] or [status-name] syntax in move descriptions
    BRACKET_PATTERN = r"\[([^\]]+)\]"

    def __init__(self) -> None:
        """Initialize converter."""
        self.created_tags: set[str] = set()
        self.created_statuses: set[str] = set()

    def convert(self, danger: DangerActor, actor_id: str | None = None) -> dict[str, Any]:
        """
        Convert a DangerActor to Foundry actor JSON.

        Args:
            danger: DangerActor to convert
            actor_id: Optional actor ID; generated if not provided

        Returns:
            Foundry actor JSON object
        """
        if actor_id is None:
            actor_id = str(uuid.uuid4())

        # Parse bracket syntax in moves to auto-create tags/statuses
        self._parse_bracket_syntax(danger)

        # Apply auto-created items to danger
        self._apply_auto_created_items(danger)

        # Convert to Foundry format using DangerActor's built-in method
        actor_json = danger.to_foundry_actor(actor_id)

        # Enhance with additional validations and processing
        self._enhance_actor(actor_json)

        return actor_json

    def _parse_bracket_syntax(self, danger: DangerActor) -> None:
        """
        Parse [tag] and [status] syntax in move descriptions.

        Extracts referenced tags and statuses for auto-creation.
        """
        for move in danger.gm_moves:
            # Find all bracketed references
            for match in re.finditer(self.BRACKET_PATTERN, move.description):
                bracket_content = match.group(1).strip()

                # Try to guess if it's a tag or status
                # Status indicators: numbers, "condition", "status"
                if self._looks_like_status(bracket_content):
                    if bracket_content not in self.created_statuses:
                        self.created_statuses.add(bracket_content)
                        # Create status with default category
                        status = DangerStatus(
                            name=bracket_content,
                            category=StatusCategory.NONE,
                        )
                        danger.statuses.append(status)
                else:
                    # Treat as tag
                    if bracket_content not in self.created_tags:
                        self.created_tags.add(bracket_content)
                        tag_type = self._infer_tag_type(bracket_content)
                        tag = Tag(
                            name=bracket_content,
                            tag_type=tag_type,
                        )
                        danger.tags.append(tag)

    def _looks_like_status(self, text: str) -> bool:
        """Heuristically determine if bracketed text is a status."""
        text_lower = text.lower()

        # Common status indicators
        status_keywords = {
            "caught",
            "harmed",
            "exposed",
            "poisoned",
            "fried",
            "blinded",
            "silenced",
            "paranoid",
            "seduced",
        }

        if any(keyword in text_lower for keyword in status_keywords):
            return True

        # If followed by number (like [fried-3]), likely a status
        if re.search(r"-\d+$", text):
            return True

        return False

    def _infer_tag_type(self, tag_name: str) -> TagType:
        """Infer tag type from tag name."""
        tag_lower = tag_name.lower()

        if any(word in tag_lower for word in ("power", "ability", "strength", "force", "skill")):
            return TagType.POWER
        if any(word in tag_lower for word in ("weak", "vulnerable", "fear", "scared", "hurt")):
            return TagType.WEAKNESS
        if any(word in tag_lower for word in ("gun", "weapon", "tool", "gear", "equipment", "car")):
            return TagType.LOADOUT
        if any(word in tag_lower for word in ("known", "love", "hate", "friend", "enemy", "ally")):
            return TagType.RELATIONSHIP

        return TagType.STORY

    def _apply_auto_created_items(self, danger: DangerActor) -> None:
        """
        Apply auto-created items to danger.

        Ensures no duplicates are added.
        """
        existing_tag_names = {tag.name.lower() for tag in danger.tags}
        existing_status_names = {status.name.lower() for status in danger.statuses}

        # Filter to avoid duplicates
        self.created_tags = {
            tag for tag in self.created_tags if tag.lower() not in existing_tag_names
        }
        self.created_statuses = {
            status
            for status in self.created_statuses
            if status.lower() not in existing_status_names
        }

    def _enhance_actor(self, actor_json: dict[str, Any]) -> None:
        """
        Apply enhancements and validations to the actor JSON.

        Args:
            actor_json: Foundry actor JSON to enhance
        """
        system = actor_json.get("system", {})

        # Ensure required fields have defaults
        if not system.get("alias"):
            system["alias"] = "?????"
        if "useAlias" not in system:
            system["useAlias"] = True
        if "locked" not in system:
            system["locked"] = False
        if not system.get("version"):
            system["version"] = "3.0.0"

        # Ensure items is a list
        if "items" not in actor_json:
            actor_json["items"] = []

        # Enhance items with required Foundry fields for import
        for item in actor_json.get("items", []):
            if "_id" not in item:
                item["_id"] = str(uuid.uuid4())

            # Add required Foundry metadata fields for proper import
            if "img" not in item:
                item["img"] = "icons/svg/item-bag.svg"
            if "effects" not in item:
                item["effects"] = []
            if "folder" not in item:
                item["folder"] = None
            if "sort" not in item:
                item["sort"] = 0
            if "flags" not in item:
                item["flags"] = {}
            if "ownership" not in item:
                item["ownership"] = {"default": 0}

        # Clean up HTML in fields
        for field in ("biography", "description", "short_description", "gmnotes"):
            if field in system and system[field]:
                system[field] = self._clean_html_field(system[field])

    def _clean_html_field(self, text: str) -> str:
        """Clean potential HTML in text fields."""
        if not text:
            return text

        # For now, just escape < and > if they're not valid HTML tags
        # More sophisticated HTML handling can be added as needed
        # Remove any control characters
        text = "".join(char for char in text if ord(char) >= 32 or char in "\n\t")

        return text.strip()


def convert_danger_to_foundry(
    danger: DangerActor,
    actor_id: str | None = None,
) -> dict[str, Any]:
    """
    Convenience function to convert a danger to Foundry format.

    Args:
        danger: DangerActor to convert
        actor_id: Optional actor ID

    Returns:
        Foundry actor JSON
    """
    converter = DangerToActorConverter()
    return converter.convert(danger, actor_id)
