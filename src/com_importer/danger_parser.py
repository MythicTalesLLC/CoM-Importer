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

    # Condition keywords that indicate a move is triggered by conditions
    MOVE_CONDITION_KEYWORDS = ("when", "if", "whenever", "each", "at the end", "at the start")

    # Pattern to detect spectrum entries (e.g., "Hurt: 0/4", "Health: 1/5")
    SPECTRUM_PATTERN = r"([\w\s]+?):\s*(\d+)/(\d+)"  # "Name: current/max" format
    # Alternative pattern for "GET INTO TROUBLE X / HURT OR SUBDUE Y" format
    # Also matches OCR'd numbers (S→5, O→0, l→1, I→1)
    SPECTRUM_ALT_PATTERN = r"([A-Z][A-Z\s]+?)\s+([0-9SOIl]+)\s*/\s*([A-Z][A-Z\s]+?)\s+([0-9SOIl]+)"

    # OCR correction mapping for common misreads in spectrum values
    OCR_DIGIT_MAP = {
        "S": "5",
        "O": "0",
        "I": "1",
        "l": "1",
        "Z": "2",
        "B": "8",
    }

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

            # Stop if we hit a section marker
            # Recognized section starters:
            # - Standard: "keyword:" (mythos:, logos:, rating:, spectrum:, move:, tag:, status:)
            # - Spectrum format: "NAME NUMBER / NAME NUMBER" (all caps)
            # - Bullet points: "• " or "- " (moves/abilities)
            if stripped:
                # Check for standard section headers
                if re.match(r"^(mythos|logos|rating|spectrum|move|tag|status)[:\s]", stripped):
                    if in_description:
                        break
                    continue

                # Check for spectrum alt format: "WORD NUMBER / WORD NUMBER"
                if re.match(r"^([A-Z][A-Z\s]+?)\s+\d+\s*/\s*([A-Z][A-Z\s]+?)\s+\d+", line.strip()):
                    if in_description:
                        break
                    continue

                # Check for bullet point (start of moves section)
                if line.lstrip().startswith(("•", "-")):
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

    def _correct_ocr_digit(self, text: str) -> str:
        """Correct common OCR misreadings of digits.

        Converts letters that look like digits back to actual digits:
        S→5, O→0, I→1, l→1, Z→2, B→8
        """
        result = text
        for letter, digit in self.OCR_DIGIT_MAP.items():
            result = result.replace(letter, digit)
        return result

    def _extract_spectrums(self, text: str) -> list[Spectrum]:
        """Extract spectrums from text.

        Handles both formats:
        - Standard: "Name: current/max" (e.g., "Health: 2/4")
        - Alternative: "NAME X / NAME Y" (e.g., "GET INTO TROUBLE 3 / HURT OR SUBDUE 2")
        """
        spectrums = []
        seen_spectrum_names = set()

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

        # Try standard pattern first: "Name: current/max"
        for match in re.finditer(self.SPECTRUM_PATTERN, spectrum_text):
            name = match.group(1).strip()
            current = int(match.group(2))
            max_tier = int(match.group(3))

            # Filter out false positives
            if (
                len(name) < 50
                and name.lower()
                not in {
                    "description",
                    "biology",
                }
                and name.lower() not in seen_spectrum_names
            ):
                spectrum = Spectrum(
                    name=name,
                    max_tier=max_tier,
                    current_tier=current,
                    pips=0,
                )
                spectrums.append(spectrum)
                seen_spectrum_names.add(name.lower())

        # Try alternative pattern: "GET INTO TROUBLE 3 / HURT OR SUBDUE 2"
        # Matches with flexible digit patterns (handles OCR errors like S→5)
        for match in re.finditer(self.SPECTRUM_ALT_PATTERN, spectrum_text):
            name1 = match.group(1).strip()
            value1_raw = match.group(2)
            name2 = match.group(3).strip()
            value2_raw = match.group(4)

            # Correct OCR digit misreadings
            value1_str = self._correct_ocr_digit(value1_raw)
            value2_str = self._correct_ocr_digit(value2_raw)

            try:
                current1 = int(value1_str)
                current2 = int(value2_str)
            except ValueError:
                # Skip if we can't parse the values even after correction
                continue

            # Add both as separate spectrums
            if name1.lower() not in seen_spectrum_names and len(name1) < 50:
                spectrum1 = Spectrum(
                    name=name1,
                    max_tier=3,  # Default to 3 for these types
                    current_tier=current1,
                    pips=0,
                )
                spectrums.append(spectrum1)
                seen_spectrum_names.add(name1.lower())

            if name2.lower() not in seen_spectrum_names and len(name2) < 50:
                spectrum2 = Spectrum(
                    name=name2,
                    max_tier=3,  # Default to 3 for these types
                    current_tier=current2,
                    pips=0,
                )
                spectrums.append(spectrum2)
                seen_spectrum_names.add(name2.lower())

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
        """Extract moves matching a specific type pattern.

        Filters out false positives from patterns found inside parentheses.
        """
        moves = []

        # Find all occurrences of the type pattern
        for match in re.finditer(type_pattern, text, re.IGNORECASE):
            start_pos = match.start()

            # Check if this match is inside parentheses - if so, skip it
            # Count open/close parens before match
            before_match = text[:start_pos]
            open_parens = before_match.count("(") - before_match.count(")")
            if open_parens > 0:
                # We're inside parentheses, skip this match
                continue

            end_pos = start_pos + 300  # Grab next 300 chars

            # Find the move text
            move_text = text[start_pos : min(end_pos, len(text))]
            lines = move_text.split("\n")

            # First line is usually the header
            name = lines[0].replace(" Move", "").strip()
            description = " ".join(lines[1:]).strip()

            # Filter out very short names which are likely false positives
            if name and len(name) > 3 and description and len(description) > 5:
                moves.append(
                    GMMove(
                        name=name,
                        description=description,
                        move_type=move_type,
                    )
                )

        return moves

    def _extract_custom_moves(self, text: str) -> list[GMMove]:
        """Extract custom moves from bullet points.

        Captures both:
        - Conditional moves: "When X happens, Y" or "If condition: action"
        - Simple moves/abilities: "Get someone to like her (friendly-2)"
        - Moves marked with "(hard move)" or "(soft move)"
        """
        moves = []
        seen_names = set()

        # Look for all potential move lines
        lines = text.split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Skip section headers and other non-moves
            if line.endswith(":") or line.isupper():
                continue

            # Check if line is a potential move by looking for:
            # 1. Bullet points (•, -, *)
            # 2. Lines containing "(hard/soft move)" markers
            # 3. Lines starting with move keywords
            is_potential_move = False

            # Strip common bullet characters if present
            text_content = line
            if line[0] in "•-*":
                text_content = line.lstrip("•-* ").strip()
                is_potential_move = True
            elif "(hard move)" in line.lower() or "(soft move)" in line.lower():
                text_content = line
                is_potential_move = True
            elif any(
                line.lower().startswith(keyword)
                for keyword in (
                    "when ",
                    "if ",
                    "get ",
                    "slam ",
                    "accelerate",
                    "takes ",
                    "rolls ",
                    "spends",
                )
            ):
                text_content = line
                is_potential_move = True

            if not is_potential_move or not text_content:
                continue

            # Skip if we've already added this
            if text_content.lower() in seen_names:
                continue

            # Determine move type based on content
            move_type = MoveType.CUSTOM
            if "(hard move)" in text_content.lower():
                move_type = MoveType.HARD
                name = text_content.replace("(hard move)", "").replace("(Hard Move)", "").strip()
            elif "(soft move)" in text_content.lower():
                move_type = MoveType.SOFT
                name = text_content.replace("(soft move)", "").replace("(Soft Move)", "").strip()
            else:
                # Check for condition keywords
                if any(word in text_content.lower() for word in self.MOVE_CONDITION_KEYWORDS):
                    move_type = MoveType.CUSTOM

                name = text_content

            # If there's a colon, split into name and description
            if ":" in text_content:
                name, desc = text_content.split(":", 1)
                name = name.strip()
                desc = desc.strip()
            else:
                # For simple moves without colons, use the full text as name
                # Extract just the main part (before parenthetical notes)
                if "(" in name:
                    name = name.split("(")[0].strip()
                desc = text_content

            if name and name.strip():
                moves.append(
                    GMMove(
                        name=name.strip(),
                        description=desc.strip() if desc.strip() else name.strip(),
                        move_type=move_type,
                    )
                )
                seen_names.add(text_content.lower())

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
