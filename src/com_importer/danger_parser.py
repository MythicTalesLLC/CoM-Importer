"""
Parser for converting text descriptions of dangers into structured DangerActor objects.

Handles parsing of text from rulebooks, PDFs, and user input.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .com_schema import (
    DangerActor,
    DangerStatus,
    GMMove,
    MoveType,
    Spectrum,
    StatusCategory,
    Tag,
    TagType,
)


@dataclass
class ParsingError:
    """Represents a parsing error or warning."""

    section: str
    message: str
    severity: str = "warning"  # "warning" or "error"


class DangerParser:
    """Parses textual descriptions of dangers into DangerActor objects."""

    # Pattern to match danger rating (e.g., "Danger Rating: 3" or "Rating 3")
    DANGER_RATING_PATTERN = r"(?:danger\s+)?rating[:\s]+(\d+)"

    # Pattern to detect move types in text
    HARD_MOVE_PATTERN = r"hard\s+(?:danger\s+)?move"
    SOFT_MOVE_PATTERN = r"soft\s+(?:danger\s+)?move|soft\s+(?:move|option)"
    CUSTOM_MOVE_PATTERN = r"custom\s+move|when\s+.*?:"

    # Pattern to detect spectrum entries (e.g., "Hurt: 0/4", "Health: 1/5")
    SPECTRUM_PATTERN = r"([\w\s]+?):\s*(\d+)/(\d+)"  # "Name: current/max" format

    # Pattern for tags in brackets
    TAG_PATTERN = r"\[([^\]]+)\]"

    def __init__(self) -> None:
        """Initialize the parser."""
        self.errors: list[ParsingError] = []

    def parse(self, text: str) -> tuple[DangerActor, list[ParsingError]]:
        """
        Parse danger text into a DangerActor.

        Args:
            text: Raw text describing the danger

        Returns:
            Tuple of (DangerActor, list of ParsingErrors)
        """
        self.errors = []
        text = text.strip()

        if not text:
            self.errors.append(ParsingError("input", "Input text is empty", "error"))
            return self._empty_danger(), self.errors

        # Extract sections
        name = self._extract_name(text)
        mythos = self._extract_mythos(text)
        logos = self._extract_logos(text)
        description = self._extract_description(text)
        danger_rating = self._extract_danger_rating(text)

        # Extract structured elements
        spectrums = self._extract_spectrums(text)
        gm_moves = self._extract_moves(text)
        tags = self._extract_tags_from_text(text)
        statuses = self._extract_statuses(text)

        # Build danger actor
        danger = DangerActor(
            name=name,
            mythos=mythos,
            logos=logos,
            description=description,
            danger_rating=danger_rating,
            gm_moves=gm_moves,
            spectrums=spectrums,
            tags=tags,
            statuses=statuses,
        )

        # Validation
        validation_errors = danger.validate()
        for error_msg in validation_errors:
            self.errors.append(ParsingError("validation", error_msg, "warning"))

        return danger, self.errors

    def _empty_danger(self) -> DangerActor:
        """Return an empty danger actor."""
        return DangerActor(name="Untitled Danger")

    def _extract_name(self, text: str) -> str:
        """Extract the danger name (usually first line or first bold text)."""
        lines = text.split("\n")
        for line in lines:
            line = line.strip()
            if line and not line.startswith("•") and len(line) < 100:
                # First substantial line that isn't a bullet
                return line
        return "Untitled Danger"

    def _extract_danger_rating(self, text: str) -> str | None:
        """Extract danger rating if present."""
        match = re.search(self.DANGER_RATING_PATTERN, text, re.IGNORECASE)
        if match:
            return match.group(1)
        return None

    def _extract_mythos(self, text: str) -> str:
        """Extract mythos (mythic identity) from text."""
        # Look for "Mythos:" or similar patterns
        patterns = [
            r"Mythos[:\s]+([^\n]+)",
            r"Mythic\s+(?:Identity|Self)[:\s]+([^\n]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return ""

    def _extract_logos(self, text: str) -> str:
        """Extract logos (mundane identity) from text."""
        patterns = [
            r"Logos[:\s]+([^\n]+)",
            r"Mundane\s+(?:Identity|Self|Form)[:\s]+([^\n]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return ""

    def _extract_description(self, text: str) -> str:
        """Extract main description/biography."""
        lines = text.split("\n")
        description_lines = []
        in_description = False

        for line in lines:
            stripped = line.strip().lower()

            # Skip empty lines at the start
            if not in_description and not line.strip():
                continue

            # Skip section header keywords (keyword at start like "Keyword:")
            if stripped and re.match(
                r"^(mythos|logos|rating|spectrum|move|tag|status)[:\s]", stripped
            ):
                if in_description:
                    break
                continue

            # If we haven't started description yet, the first non-empty, non-header line starts it
            if not in_description and line.strip():
                in_description = True

            if in_description:
                description_lines.append(line)

        # Remove leading empty lines from description
        while description_lines and not description_lines[0].strip():
            description_lines.pop(0)

        return "\n".join(description_lines).strip()

    def _extract_spectrums(self, text: str) -> list[Spectrum]:
        """Extract spectrums from text."""
        spectrums = []

        # Look for "Spectrum:" or "Status Spectrum:" sections
        spectrum_section = re.search(
            r"(?:status\s+)?spectrum[:\s]*(.+?)(?:move|threat|custom|hard|soft|\Z)",
            text,
            re.IGNORECASE | re.DOTALL,
        )
        if spectrum_section:
            spectrum_text = spectrum_section.group(1)
        else:
            spectrum_text = text

        # Find all patterns like "Name: current/max" or "Name: max"
        for match in re.finditer(self.SPECTRUM_PATTERN, spectrum_text):
            name = match.group(1).strip()
            current = int(match.group(2))
            max_tier = int(match.group(3))

            # Filter out false positives (very long names, etc.)
            if len(name) < 50 and name.lower() not in {
                "description",
                "biology",
            }:
                spectrum = Spectrum(
                    name=name,
                    max_tier=max_tier,
                    current_tier=current,
                    pips=0,
                )
                spectrums.append(spectrum)

        return spectrums

    def _extract_moves(self, text: str) -> list[GMMove]:
        """Extract GM moves from text."""
        moves = []

        # Split on move markers
        hard_moves = self._extract_moves_by_type(text, self.HARD_MOVE_PATTERN, MoveType.HARD)
        soft_moves = self._extract_moves_by_type(text, self.SOFT_MOVE_PATTERN, MoveType.SOFT)
        custom_moves = self._extract_custom_moves(text)

        moves.extend(hard_moves)
        moves.extend(soft_moves)
        moves.extend(custom_moves)

        if not moves:
            self.errors.append(
                ParsingError(
                    "moves",
                    "No GM moves found; add some moves manually",
                    "warning",
                )
            )

        return moves

    def _extract_moves_by_type(
        self,
        text: str,
        type_pattern: str,
        move_type: MoveType,
    ) -> list[GMMove]:
        """Extract moves matching a specific type pattern."""
        moves = []

        # Find all occurrences of the type pattern
        for match in re.finditer(type_pattern, text, re.IGNORECASE):
            start_pos = match.start()
            end_pos = start_pos + 300  # Grab next 300 chars

            # Find the move text
            move_text = text[start_pos : min(end_pos, len(text))]
            lines = move_text.split("\n")

            # First line is usually the header
            name = lines[0].replace(" Move", "").strip()
            description = " ".join(lines[1:]).strip()

            if name and description:
                moves.append(
                    GMMove(
                        name=name,
                        description=description,
                        move_type=move_type,
                    )
                )

        return moves

    def _extract_custom_moves(self, text: str) -> list[GMMove]:
        """Extract custom moves (usually triggered by conditions)."""
        moves = []

        # Look for bullet points with conditions
        lines = text.split("\n")
        for _i, line in enumerate(lines):
            if line.strip().startswith("•") or line.strip().startswith("-"):
                text_content = line.lstrip("•-").strip()

                # Check if it has a condition (contains "when", "if", ":", etc.)
                if any(word in text_content.lower() for word in ("when", "if", "whenever", "each")):
                    # Try to extract name and description
                    if ":" in text_content:
                        name, desc = text_content.split(":", 1)
                    else:
                        name = text_content[:50]
                        desc = text_content

                    if name.strip():
                        moves.append(
                            GMMove(
                                name=name.strip(),
                                description=desc.strip(),
                                move_type=MoveType.CUSTOM,
                            )
                        )

        return moves

    def _extract_tags_from_text(self, text: str) -> list[Tag]:
        """Extract tags mentioned in brackets [tag-name]."""
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
        if any(word in tag_lower for word in ("weak", "vulnerable", "fear", "hurt")):
            return TagType.WEAKNESS
        if any(word in tag_lower for word in ("gun", "weapon", "tool", "gear")):
            return TagType.LOADOUT
        if any(word in tag_lower for word in ("known", "loved", "enemy", "friend", "ally")):
            return TagType.RELATIONSHIP

        return TagType.STORY

    def _extract_statuses(self, text: str) -> list[DangerStatus]:
        """Extract status conditions from text."""
        statuses = []

        # Look for common status keywords
        status_keywords = {
            "caught": StatusCategory.COMPELLING,
            "exposed": StatusCategory.WEAKENING,
            "harmed": StatusCategory.HARM,
            "helped": StatusCategory.ADVANCE,
        }

        for keyword, category in status_keywords.items():
            if keyword in text.lower():
                status = DangerStatus(
                    name=keyword.capitalize(),
                    category=category,
                )
                statuses.append(status)

        return statuses
