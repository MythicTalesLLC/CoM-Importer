"""
Parser for converting text descriptions of characters into structured CharacterActor objects.

Handles parsing of text from rulebooks, PDFs, and user input for player characters.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .com_schema import (
    CharacterActor,
    Tag,
    TagType,
    Theme,
)


@dataclass
class ParsingError:
    """Represents a parsing error or warning."""

    section: str
    message: str
    severity: str = "warning"  # "warning" or "error"


class CharacterParser:
    """Parses textual descriptions of characters into CharacterActor objects."""

    # Pattern for character name (usually first line)
    NAME_PATTERN = r"^([^(\n]+?)(?:\s*\(.*?\))?\s*$"

    # Patterns to detect theme sections
    MYTHOS_PATTERN = (
        r"(?:mythos|mythic\s+theme)[:\s]*(.+?)(?:logos|mundane|theme|juice|status|move|ability|\Z)"
    )
    LOGOS_PATTERN = (
        r"(?:logos|mundane\s+theme)[:\s]*(.+?)(?:mist|other|theme|juice|status|move|ability|\Z)"
    )
    MIST_PATTERN = r"(?:mist\s+theme)[:\s]*(.+?)(?:juice|status|move|ability|custom|\Z)"

    # Pattern for juice/resources (e.g., "Juice: Help 0/3, Hurt 0/3")
    JUICE_PATTERN = r"juice[:\s]*help\s*(\d+).*?hurt\s*(\d+)|juice[:\s]*(\d+)/(\d+)"

    # Pattern for pronouns (e.g., "She/Her", "They/Them", "He/Him")
    PRONOUNS_PATTERN = r"(?:pronouns?|gender)[:\s]*([^,\n]+?(?:/[^,\n]+?)?)"

    # Pattern for tags in brackets
    TAG_PATTERN = r"\[([^\]]+)\]"

    # Pattern for character moves/abilities
    MOVE_PATTERN = r"(?:move|ability|power)[:\s]*([^\n]+)"

    def __init__(self) -> None:
        """Initialize the parser."""
        self.errors: list[ParsingError] = []

    def parse(self, text: str) -> tuple[CharacterActor, list[ParsingError]]:
        """
        Parse character text into a CharacterActor.

        Args:
            text: Raw text describing the character

        Returns:
            Tuple of (CharacterActor, list of ParsingErrors)
        """
        self.errors = []
        text = text.strip()

        if not text:
            self.errors.append(ParsingError("input", "Input text is empty", "error"))
            return self._empty_character(), self.errors

        # Extract basic info
        name = self._extract_name(text)
        pronouns = self._extract_pronouns(text)
        description = self._extract_description(text)

        # Extract themes with their tags
        themes = self._extract_themes(text)

        # Extract juice levels
        juice_help, juice_hurt = self._extract_juice(text)

        # Build character actor
        character = CharacterActor(
            name=name,
            pronouns=pronouns,
            description=description,
            themes=themes,
            juice_help=juice_help,
            juice_hurt=juice_hurt,
        )

        # Validation
        validation_errors = character.validate()
        for error_msg in validation_errors:
            self.errors.append(ParsingError("validation", error_msg, "warning"))

        return character, self.errors

    def _empty_character(self) -> CharacterActor:
        """Return an empty character actor."""
        return CharacterActor(name="Untitled Character")

    def _extract_name(self, text: str) -> str:
        """Extract the character name (usually first line)."""
        lines = text.split("\n")
        for line in lines:
            line = line.strip()
            if line and not line.startswith("•") and len(line) < 100:
                # Remove any parenthetical notes like (PC) or (Player)
                name = re.sub(r"\s*\([^)]*\)\s*", "", line).strip()
                if name:
                    return name
        return "Untitled Character"

    def _extract_pronouns(self, text: str) -> str:
        """Extract pronouns if present."""
        # First try labeled pattern (pronouns: She/Her)
        match = re.search(self.PRONOUNS_PATTERN, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()

        # Try to find pronouns in early lines without labels
        # Common pattern: standalone line with slashes like "She/Her" or "They/Them"
        lines = text.split("\n")
        for _i, line in enumerate(lines[:5]):  # Check first 5 lines
            line = line.strip()
            # Look for patterns like "She/Her", "He/Him", "They/Them", etc.
            if re.match(r"^[A-Za-z]+/[A-Za-z]+$", line):
                return line
        return ""

    def _extract_description(self, text: str) -> str:
        """Extract main description/biography."""
        lines = text.split("\n")
        description_lines = []
        in_description = False
        skip_keywords = {
            "mythos",
            "logos",
            "mist",
            "theme",
            "juice",
            "pronouns",
            "move",
            "ability",
            "power",
            "tag",
            "status",
        }

        for line in lines:
            stripped = line.strip().lower()

            # Skip empty lines at the start
            if not in_description and not line.strip():
                continue

            # Skip lines that are section headers
            if stripped and any(kw in stripped for kw in skip_keywords):
                if in_description:
                    break
                continue

            # Skip if it looks like a title/first line
            if not in_description and len(line.strip()) < 100:
                in_description = True
                continue

            if in_description:
                description_lines.append(line)

        return "\n".join(description_lines).strip()

    def _extract_themes(self, text: str) -> list[Theme]:
        """Extract themes (Mythos, Logos, Mist or custom) from text."""
        themes = []

        # Extract each theme type
        mythos = self._extract_theme_section(text, self.MYTHOS_PATTERN, "Mythos")
        if mythos:
            themes.append(mythos)

        logos = self._extract_theme_section(text, self.LOGOS_PATTERN, "Logos")
        if logos:
            themes.append(logos)

        mist = self._extract_theme_section(text, self.MIST_PATTERN, "Mist")
        if mist:
            themes.append(mist)

        # If no standard themes found, try to extract any custom themes
        if not themes:
            self.errors.append(
                ParsingError(
                    "themes",
                    "No themes found; add Mythos, Logos, or Mist themes manually",
                    "warning",
                )
            )

        return themes

    def _extract_theme_section(
        self,
        text: str,
        pattern: str,
        theme_name: str,
    ) -> Theme | None:
        """Extract a single theme section."""
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if not match:
            return None

        theme_content = match.group(1).strip()

        # Extract description (first few lines)
        lines = theme_content.split("\n")
        description = ""
        if lines:
            description = lines[0][:200].strip()

        # Extract tags from this theme section
        tags = []
        seen_tags = set()

        for tag_match in re.finditer(self.TAG_PATTERN, theme_content):
            tag_name = tag_match.group(1).strip()

            if tag_name.lower() not in seen_tags:
                seen_tags.add(tag_name.lower())
                tag_type = self._infer_tag_type(tag_name)
                tags.append(
                    Tag(
                        name=tag_name,
                        tag_type=tag_type,
                    )
                )

        return Theme(
            name=theme_name,
            description=description,
            tags=tags,
        )

    def _extract_juice(self, text: str) -> tuple[int, int]:
        """Extract juice (help/hurt) levels."""
        help_juice = 0
        hurt_juice = 0

        # Try pattern with explicit help/hurt labels
        match = re.search(self.JUICE_PATTERN, text, re.IGNORECASE)
        if match:
            if match.group(1):  # help/hurt format
                help_juice = int(match.group(1))
                hurt_juice = int(match.group(2))
            else:  # Combined format like "3/3"
                help_juice = int(match.group(3))
                hurt_juice = int(match.group(4))

        return help_juice, hurt_juice

    def _extract_tags_from_text(self, text: str) -> list[Tag]:
        """Extract standalone tags mentioned in brackets [tag-name]."""
        tags = []
        seen_tags = set()

        for match in re.finditer(self.TAG_PATTERN, text):
            tag_name = match.group(1).strip()

            # Skip if we've already added this tag
            if tag_name.lower() in seen_tags:
                continue
            seen_tags.add(tag_name.lower())

            # Try to infer tag type
            tag_type = self._infer_tag_type(tag_name)

            tags.append(
                Tag(
                    name=tag_name,
                    tag_type=tag_type,
                )
            )

        return tags

    def _infer_tag_type(self, tag_name: str) -> TagType:
        """Infer tag type from tag name."""
        tag_lower = tag_name.lower()

        # Simple heuristics
        if any(
            word in tag_lower
            for word in (
                "power",
                "ability",
                "strength",
                "skill",
                "strong",
            )
        ):
            return TagType.POWER
        if any(word in tag_lower for word in ("weak", "vulnerable", "fear", "hurt", "burden")):
            return TagType.WEAKNESS
        if any(word in tag_lower for word in ("gun", "weapon", "tool", "gear", "equipment")):
            return TagType.LOADOUT
        if any(
            word in tag_lower
            for word in (
                "known",
                "loved",
                "enemy",
                "friend",
                "ally",
                "crew",
                "partner",
            )
        ):
            return TagType.RELATIONSHIP

        return TagType.STORY
