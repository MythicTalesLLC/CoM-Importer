"""
Parser for converting text descriptions of dangers into structured DangerActor objects.

Handles parsing of text from rulebooks, PDFs, and user input.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .com_schema import (
    CustomAbility,
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

    # Pattern for additive Mythos Power Set rating (+★ or +1 etc.)
    MYTHOS_POWER_SET_PATTERN = r"\+[★⭐]+|\+\s*\d+\s*[★⭐]"

    # Pattern to detect move types in text
    HARD_MOVE_PATTERN = r"hard\s+(?:danger\s+)?move"
    SOFT_MOVE_PATTERN = r"soft\s+(?:danger\s+)?move|soft\s+(?:move|option)"
    CUSTOM_MOVE_PATTERN = r"custom\s+move|when\s+.*?:"

    # Condition keywords that indicate a move is triggered by conditions
    MOVE_CONDITION_KEYWORDS = ("when", "if", "whenever", "each", "at the end", "at the start")

    # Pattern to detect spectrum entries (e.g., "Hurt: 0/4", "Health: 1/5")
    SPECTRUM_PATTERN = r"([\w\s]+?):\s*(\d+)/(\d+)"  # "Name: current/max" format

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

    # Status in parentheses: (word-word-N) - ends in a digit
    STATUS_IN_PARENS_RE = re.compile(r"\(([\w][\w-]*-\d+)\)")

    # Story tag in parentheses: (word) or (multi word) - no trailing digit
    STORY_TAG_IN_PARENS_RE = re.compile(r"\(([a-zA-Z][a-zA-Z\s-]{1,30})\)")

    # Collective/Vehicle/Team note at the start of a line
    COLLECTIVE_LINE_RE = re.compile(r"^(?:Collective|Vehicle|Team)[:\s]+(.+)", re.IGNORECASE)

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
        is_mythos_power_set = self._detect_mythos_power_set(text)

        # Extract structured elements
        spectrums = [] if is_mythos_power_set else self._extract_spectrums(text)
        gm_moves, custom_abilities = self._extract_moves(text)
        tags = self._extract_tags_from_text(text)
        statuses = self._extract_statuses(text)
        collective_size, collective_note = self._extract_collective(text)

        # Build danger actor
        danger = DangerActor(
            name=name,
            mythos=mythos,
            logos=logos,
            description=description,
            danger_rating=danger_rating,
            is_mythos_power_set=is_mythos_power_set,
            gm_moves=gm_moves,
            custom_abilities=custom_abilities,
            spectrums=spectrums,
            tags=tags,
            statuses=statuses,
            collective_size=collective_size,
            collective_note=collective_note,
        )

        # Validation
        validation_errors = danger.validate()
        for error_msg in validation_errors:
            self.errors.append(ParsingError("validation", error_msg, "warning"))

        return danger, self.errors

    def _empty_danger(self) -> DangerActor:
        """Return an empty danger actor."""
        return DangerActor(name="Untitled Danger")

    def _strip_section_prefix(self, line: str) -> str:
        """Strip common OCR section prefixes from the start of a line.

        Some rulebooks have section labels (ACT, HARD, SOFT) before move names
        that OCR picks up. This strips them to reveal the actual move.

        Examples:
            "ACT Inquisitive: ..." → "Inquisitive: ..."
            "HARD MOVE Brutally bludgeon: ..." → "Brutally bludgeon: ..."
        """
        if not line:
            return line

        prefixes = ("act ", "hard move ", "soft move ", "hard ", "soft ")
        line_lower = line.lower()

        for prefix in prefixes:
            if line_lower.startswith(prefix):
                return line[len(prefix) :].strip()

        return line

    def _extract_name(self, text: str) -> str:
        """Extract the danger name (usually first line or first bold text)."""
        lines = text.split("\n")
        for line in lines:
            line = line.strip()
            if line and not line.startswith("•") and len(line) < 100:
                # First substantial line that isn't a bullet
                name = line
                # Remove stars (★ and ⭐) which represent danger level
                name = re.sub(r"[★⭐]+\s*", "", name).strip()
                # Remove trailing garbage like "kk *&" by keeping only reasonable characters
                # Keep only: letters, numbers, spaces, hyphens, apostrophes
                cleaned = re.sub(r"[^a-zA-Z0-9\s\-'].*$", "", name).strip()
                if cleaned:
                    name = cleaned
                # Threat names are typically 1-3 words - remove trailing short garbage words
                words = name.split()
                # If last word is short (len < 3) and all lowercase, it's likely OCR garbage
                while words and len(words[-1]) < 3 and words[-1].islower():
                    words.pop()
                if words:
                    name = " ".join(words)
                return name if name else line
        return "Untitled Danger"

    def _extract_danger_rating(self, text: str) -> str | None:
        """Extract danger rating if present.

        Looks for:
        - "Rating 3" or "Danger Rating: 3"
        - Stars: ★★★ or ⭐⭐⭐ (count them)
        - Additive Mythos Power Set: +★ or +★★
        """
        # First try the standard pattern
        match = re.search(self.DANGER_RATING_PATTERN, text, re.IGNORECASE)
        if match:
            return match.group(1)

        # Try to count stars in the first line (danger level indicator)
        lines = text.split("\n")
        if lines:
            first_line = lines[0]
            # Check for additive Mythos Power Set format (+★)
            additive_match = re.search(self.MYTHOS_POWER_SET_PATTERN, first_line)
            if additive_match:
                # Count additive stars
                star_count = first_line.count("★") + first_line.count("⭐")
                return f"+{star_count}" if star_count > 0 else "+1"

            # Count filled stars for standard rating
            star_count = first_line.count("★") + first_line.count("⭐")
            if star_count > 0:
                return str(star_count)

        return None

    def _detect_mythos_power_set(self, text: str) -> bool:
        """Detect whether this entry is a Mythos Power Set (additive +★ rating, no spectrum)."""
        lines = text.split("\n")
        if lines:
            first_line = lines[0]
            if re.search(self.MYTHOS_POWER_SET_PATTERN, first_line):
                return True
        return False

    def _extract_collective(self, text: str) -> tuple[int, str]:
        """Extract collective size and note from Collective/Vehicle/Team lines.

        Returns:
            Tuple of (collective_size, collective_note)
        """
        collective_size = 0
        collective_note = ""

        for line in text.split("\n"):
            stripped = line.strip()
            m = self.COLLECTIVE_LINE_RE.match(stripped)
            if m:
                note = m.group(1).strip()
                collective_note = note

                # Try to extract a number from the note as the size factor
                size_match = re.search(r"\b(\d+)\b", note)
                if size_match:
                    collective_size = int(size_match.group(1))
                elif re.search(r"\bmany\b|\blarge\b|\bnumerous\b", note, re.IGNORECASE):
                    collective_size = 5
                elif re.search(r"\bfew\b|\bsmall\b", note, re.IGNORECASE):
                    collective_size = 2
                else:
                    collective_size = 1
                break

        return collective_size, collective_note

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
            stripped = line.strip()
            stripped_lower = stripped.lower()

            # Skip empty lines at the start
            if not in_description and not stripped:
                continue

            if stripped:
                # Stop at standard section headers
                if re.match(
                    r"^(mythos|logos|rating|spectrum|move|tag|status|collective|vehicle|team)[:\s]",
                    stripped_lower,
                ):
                    if in_description:
                        break
                    continue

                # Stop at ALL-CAPS spectrum line (e.g. "HURT OR SUBDUE 3 / GET INTO TROUBLE 4")
                if self._is_spectrum_line(stripped):
                    if in_description:
                        break
                    continue

                # Stop at bullet point (start of moves section)
                if line.lstrip().startswith(("•", "-", "*", "¢")):
                    if in_description:
                        break
                    continue

                # Stop at bold custom ability block
                if stripped.startswith("**") and ":" in stripped:
                    if in_description:
                        break
                    continue

            # First non-empty, non-header line starts the description
            if not in_description and stripped:
                in_description = True

            if in_description:
                description_lines.append(line)

        # Remove leading/trailing empty lines
        while description_lines and not description_lines[0].strip():
            description_lines.pop(0)
        while description_lines and not description_lines[-1].strip():
            description_lines.pop()

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

    # --- Spectrum helpers ---------------------------------------------------

    # Matches all-caps spectrum line: "HURT OR SUBDUE 3 / GET INTO TROUBLE 4"
    _SPECTRUM_ALLCAPS_RE = re.compile(
        r"^([A-Z][A-Z\s]+?)\s+([0-9]+|-)\s*(?:/\s*([A-Z][A-Z\s]+?)\s+([0-9]+|-))?$"
    )
    # Space-separated pairs WITHOUT slash: "CORRUPT 3 BRIBE -"
    _SPECTRUM_SPACE_PAIRS_RE = re.compile(
        r"^([A-Z][A-Z]+(?:\s+[A-Z]+)*)\s+([0-9]+|-)\s+([A-Z][A-Z]+(?:\s+[A-Z]+)*)\s+([0-9]+|-)$"
    )
    # Standard "Name: current/max" format
    _SPECTRUM_SLASH_RE = re.compile(r"^([\w][\w\s]+?):\s*(\d+)\s*/\s*(\d+)$")

    def _is_spectrum_line(self, line: str) -> bool:
        """Return True if *line* looks like a spectrum declaration."""
        s = line.strip()
        if not s:
            return False
        # Explicit "Spectrum:" header
        if re.match(r"(?:status\s+)?spectrum[:\s]", s, re.IGNORECASE):
            return True
        # "Name: current/max"
        if self._SPECTRUM_SLASH_RE.match(s):
            return True
        # ALL-CAPS word(s) + digit or dash (with optional slash-separated second)
        if self._SPECTRUM_ALLCAPS_RE.match(s):
            return True
        # Space-separated pairs: "CORRUPT 3 BRIBE -"
        if self._SPECTRUM_SPACE_PAIRS_RE.match(s):
            return True
        return False

    def _parse_spectrum_line(self, line: str) -> list[Spectrum]:
        """Parse one line into 1–4 Spectrum objects.

        Handles:
        - "Name: current/max"  e.g. "Health: 2/4"
        - "NAME N / NAME2 M"   e.g. "GET INTO TROUBLE 3 / HURT OR SUBDUE 4"
        - "NAME N NAME2 M"     space-separated, no slash
        - "NAME -"             dash means immune/unlimited (max_tier=None)
        - Handles OCR digit confusion (S→5, O→0, etc.)
        """
        s = line.strip()
        results: list[Spectrum] = []

        # Strip a leading "Spectrum:" label
        s = re.sub(r"^(?:status\s+)?spectrum[:\s]*", "", s, flags=re.IGNORECASE).strip()

        # "Name: current/max"
        m = self._SPECTRUM_SLASH_RE.match(s)
        if m:
            name = m.group(1).strip()
            max_tier = int(m.group(3))
            current = int(m.group(2))
            return [Spectrum(name=name, max_tier=max_tier, current_tier=current, pips=0)]

        # ALL-CAPS formats; parse tokens to find (name, value) pairs
        parts = self._split_spectrum_tokens(s)
        for name, raw_val in parts:
            name = name.strip()
            if not name or len(name) > 60:
                continue
            if raw_val == "-" or not raw_val:
                max_tier = None
            else:
                corrected = self._correct_ocr_digit(raw_val)
                try:
                    max_tier = int(corrected)
                except ValueError:
                    max_tier = None
            results.append(
                Spectrum(
                    name=name,
                    max_tier=max_tier,
                    current_tier=max_tier if max_tier is not None else 0,
                    pips=0,
                )
            )
        return results

    def _split_spectrum_tokens(self, s: str) -> list[tuple[str, str]]:
        """Split a spectrum line into (name, value) pairs.

        Handles slash-separated and space-separated ALL-CAPS formats.
        E.g. "GET INTO TROUBLE 3 / HURT OR SUBDUE 4"
             → [("GET INTO TROUBLE","3"),("HURT OR SUBDUE","4")]
             "CORRUPT 3 BRIBE -" → [("CORRUPT","3"),("BRIBE","-")]
        """
        parts: list[tuple[str, str]] = []
        # Split on slash first
        segments = [seg.strip() for seg in s.split("/")]
        for seg in segments:
            seg = seg.strip()
            if not seg:
                continue
            # Each segment: one or more ALL_CAPS words followed by a value token
            # Value token: digits, OCR-digit chars, or "-"
            m = re.match(r"^([A-Z][A-Z\s]+?)\s+([0-9SOIlZB]+|-)$", seg)
            if m:
                parts.append((m.group(1).strip(), m.group(2).strip()))
            else:
                # Try space-separated within the segment: grab consecutive pairs
                tokens = seg.split()
                i = 0
                while i < len(tokens):
                    # Collect all-caps name tokens
                    name_tokens = []
                    while i < len(tokens) and re.match(r"^[A-Z]+$", tokens[i]):
                        name_tokens.append(tokens[i])
                        i += 1
                    # Next token should be the value
                    if name_tokens and i < len(tokens):
                        val = tokens[i]
                        if re.match(r"^[0-9SOIlZB]+$", val) or val == "-":
                            parts.append((" ".join(name_tokens), val))
                            i += 1
                    else:
                        i += 1
        return parts

    def _extract_spectrums(self, text: str) -> list[Spectrum]:
        """Extract spectrums by scanning each line of the text.

        Uses _is_spectrum_line / _parse_spectrum_line for all formats:
        - "Name: current/max"
        - "NAME N / NAME M"  (slash-separated ALL-CAPS)
        - "NAME N NAME M"    (space-separated ALL-CAPS, common in printed books)
        - "NAME -"           (dash = immune/unlimited)
        Also handles an explicit "Spectrum:" section header.
        """
        spectrums: list[Spectrum] = []
        seen: set[str] = set()

        # First, check for an explicit "Spectrum:" section and prefer those lines
        in_spectrum_section = False

        for line in text.split("\n"):
            stripped = line.strip()

            # An explicit "Spectrum:" header opens the section
            if re.match(r"^(?:status\s+)?spectrum[:\s]", stripped, re.IGNORECASE):
                in_spectrum_section = True
                # The header itself may contain data: "Spectrum: Health 2/4"
                remainder = re.sub(
                    r"^(?:status\s+)?spectrum[:\s]*", "", stripped, flags=re.IGNORECASE
                ).strip()
                if remainder:
                    for sp in self._parse_spectrum_line(remainder):
                        if sp.name.lower() not in seen:
                            spectrums.append(sp)
                            seen.add(sp.name.lower())
                continue

            # Close spectrum section when we hit bullets or known section starters
            if in_spectrum_section:
                if not stripped:
                    continue
                if stripped[0] in "•-*¢" or re.match(
                    r"^(mythos|logos|move|tag|status|hard|soft|custom|collective|vehicle|team)[:\s]",
                    stripped,
                    re.IGNORECASE,
                ):
                    in_spectrum_section = False
                    continue
                # Parse this line as a spectrum
                parsed = self._parse_spectrum_line(stripped)
                for sp in parsed:
                    if sp.name.lower() not in seen:
                        spectrums.append(sp)
                        seen.add(sp.name.lower())
                continue

            # Outside an explicit section: scan any line that looks like a spectrum
            if self._is_spectrum_line(stripped):
                for sp in self._parse_spectrum_line(stripped):
                    if sp.name.lower() not in seen:
                        spectrums.append(sp)
                        seen.add(sp.name.lower())

        return spectrums

    def _extract_moves(self, text: str) -> tuple[list[GMMove], list[CustomAbility]]:
        """Extract GM moves and custom abilities from text.

        Returns:
            Tuple of (gm_moves, custom_abilities)
        """
        moves = []
        custom_abilities = []

        # Check if text contains OCR bullet artifacts (¢) - if so, skip section-based extraction
        # OCR'd text usually doesn't have explicit "Hard Moves:" sections, just bullet points
        has_ocr_bullets = "¢" in text

        # Extract hard/soft moves by type only if this isn't OCR'd text
        if not has_ocr_bullets:
            hard_moves = self._extract_moves_by_type(text, self.HARD_MOVE_PATTERN, MoveType.HARD)
            soft_moves = self._extract_moves_by_type(text, self.SOFT_MOVE_PATTERN, MoveType.SOFT)
            moves.extend(hard_moves)
            moves.extend(soft_moves)

        # Extract custom moves and custom abilities from bullet points
        custom_moves, custom_abs = self._extract_custom_moves(text)

        moves.extend(custom_moves)
        custom_abilities.extend(custom_abs)

        if not moves and not custom_abilities:
            self.errors.append(
                ParsingError(
                    "moves",
                    "No GM moves or custom abilities found; add some manually",
                    "warning",
                )
            )

        return moves, custom_abilities

    def _extract_moves_by_type(
        self,
        text: str,
        type_pattern: str,
        move_type: MoveType,
    ) -> list[GMMove]:
        """Extract moves matching a specific type pattern.

        Filters out false positives from patterns found inside parentheses or descriptions.
        Only matches patterns that appear at/near the start of a line (after bullets).
        """
        moves = []

        # Find all occurrences of the type pattern
        for match in re.finditer(type_pattern, text, re.IGNORECASE):
            start_pos = match.start()

            # Check if this match is inside parentheses - if so, skip it
            before_match = text[:start_pos]
            open_parens = before_match.count("(") - before_match.count(")")
            if open_parens > 0:
                continue

            # Require the match to be at the start of a line (after bullets/whitespace only)
            # OR be in the first few positions of a line before more text
            line_start = before_match.rfind("\n") + 1
            text_before_on_line = before_match[line_start:]

            # The text before should be empty, whitespace, or just bullet chars
            # Don't match if there's significant text before the pattern on the line
            if text_before_on_line:
                # Check if it's only bullets/whitespace
                non_bullet_text = re.sub(r"[•\-*¢\s\t]", "", text_before_on_line)
                if non_bullet_text:
                    # There's actual text before the pattern, skip it
                    continue

            end_pos = start_pos + 300

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

    def _extract_inline_move_metadata(self, desc: str) -> tuple[list[str], list[str], bool, str]:
        """Extract inline statuses, story tags, optional flag, and effect type from a description.

        Inline formats per the schema:
        - (word-word-N)  → status tag (ends in -digit)
        - (word)         → story tag (no trailing digit, 2–30 chars)
        - (optional)     → sets optional=True (consumed, not a tag)
        - "create a new Danger" / "Deny Them Something" → effect_type="createDanger"/"special"

        Returns:
            (statuses, story_tags, is_optional, effect_type)
        """
        statuses: list[str] = []
        story_tags: list[str] = []
        is_optional = False
        effect_type = ""

        # Check for "(optional)" flag
        if re.search(r"\(optional\)", desc, re.IGNORECASE):
            is_optional = True

        # Check for special effect markers
        if re.search(r"create\s+a\s+new\s+danger", desc, re.IGNORECASE):
            effect_type = "createDanger"
        elif re.search(r"deny\s+them\s+something\s+they\s+want", desc, re.IGNORECASE):
            effect_type = "special"

        # Extract (status-N) patterns
        for m in self.STATUS_IN_PARENS_RE.finditer(desc):
            tag = m.group(1)
            if tag.lower() not in {"optional", "hard move", "soft move"}:
                statuses.append(tag)

        # Extract (story tag) patterns — exclude known false positives
        _excluded = {
            "optional",
            "hard move",
            "soft move",
            "hard",
            "soft",
        }
        for m in self.STORY_TAG_IN_PARENS_RE.finditer(desc):
            tag = m.group(1).strip()
            tag_lower = tag.lower()
            # Skip if it's already captured as a status
            if any(tag_lower == s.lower() for s in statuses):
                continue
            # Skip (optional) and move type markers
            if tag_lower in _excluded:
                continue
            # Skip if it ends with a digit (already caught as status above)
            if re.search(r"-\d+$", tag):
                continue
            story_tags.append(tag)

        return statuses, story_tags, is_optional, effect_type

    def _extract_custom_moves(self, text: str) -> tuple[list[GMMove], list[CustomAbility]]:
        """Extract custom moves and abilities from bullet points with multi-line descriptions.

        Captures both:
        - GM Moves (hard/soft): Bullet points with actions
        - Custom Abilities: **Name:** blocks (special rules)
        Continues reading lines after move name to capture full descriptions.

        Also extracts inline move metadata per schema rules:
        - (status-N) parentheticals → GMMove.statuses list
        - (story tag) parentheticals → GMMove.tags list
        - (optional) → GMMove.optional = True
        - "create a new Danger" → GMMove.effect_type = "createDanger"

        Returns:
            Tuple of (gm_moves, custom_abilities)
        """
        moves = []
        custom_abilities = []
        seen_names = set()

        _MOVE_START_KWS = (
            "when ",
            "if ",
            "get ",
            "slam ",
            "accelerate",
            "takes ",
            "rolls ",
            "spends",
        )

        # Look for all potential move lines
        lines = text.split("\n")
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            i += 1

            if not line:
                continue

            # Skip spectrum lines — they are not moves
            if self._is_spectrum_line(line):
                continue

            # Skip section headers and other non-moves
            if line.endswith(":") or line.isupper():
                continue

            # Strip common OCR section prefixes (like "ACT ", "HARD ", "SOFT ")
            # These appear before move names in OCR text
            line = self._strip_section_prefix(line)

            # Check if line is a potential move by looking for:
            # 1. Custom abilities: **NAME:** blocks
            # 2. Bullet points (•, -, *)
            # 3. Lines containing "(hard/soft move)" markers
            # 4. Lines starting with move keywords
            is_potential_move = False

            # Check for custom abilities first (before stripping bullets)
            if line.startswith("**") and ":" in line:
                text_content = line
                is_potential_move = True
            # Strip common bullet characters if present (including OCR variants like ¢)
            elif line and line[0] in "•-*¢":
                text_content = line.lstrip("•-*¢ ").strip()
                is_potential_move = True
            elif "(hard move)" in line.lower() or "(soft move)" in line.lower():
                text_content = line
                is_potential_move = True
            elif any(line.lower().startswith(keyword) for keyword in _MOVE_START_KWS):
                text_content = line
                is_potential_move = True

            if not is_potential_move or not text_content:
                continue

            # Strip common OCR section prefixes again after bullet removal
            text_content = self._strip_section_prefix(text_content)

            # Skip if we've already added this
            if text_content.lower() in seen_names:
                continue

            # Determine move type based on schema rules:
            # - Contains "(hard move)" → HARD
            # - Starts with **NAME:** → CUSTOM (custom ability)
            # - Otherwise (bullet point) → SOFT
            move_type = MoveType.SOFT  # Default for bullets

            # Check for explicit "(hard move)" marker
            if "(hard move)" in text_content.lower():
                move_type = MoveType.HARD
                name = text_content.replace("(hard move)", "").replace("(Hard Move)", "").strip()
            # Check if it's a custom ability (bold block with colon)
            elif text_content.startswith("**") and ":" in text_content:
                move_type = MoveType.CUSTOM
                name = text_content
            else:
                name = text_content

            # If there's a colon, split into name and description
            if ":" in text_content:
                name, desc = text_content.split(":", 1)
                name = name.strip()
                # Remove any move type markers from the split name
                name = (
                    name.replace("(hard move)", "")
                    .replace("(Hard Move)", "")
                    .replace("(soft move)", "")
                    .replace("(Soft Move)", "")
                    .strip()
                )
                desc = desc.strip()

                # Collect continuation lines for multi-line descriptions
                description_lines = [desc] if desc else []
                while i < len(lines):
                    next_line = lines[i].strip()
                    if not next_line:
                        i += 1
                        continue
                    # Check if this is a new move (bullet point or keyword at start)
                    if next_line[0] in "•-*¢" or any(
                        next_line.lower().startswith(kw) for kw in _MOVE_START_KWS
                    ):
                        break

                    # If previous line had unclosed parens, always continue
                    if description_lines:
                        last_line = description_lines[-1]
                        open_parens = last_line.count("(") - last_line.count(")")
                        if open_parens > 0:
                            pass  # fall through to append

                    description_lines.append(next_line)
                    i += 1

                    if len(description_lines) >= 10:
                        break

                desc = " ".join(description_lines).strip()
            else:
                # For simple moves without colons, collect multi-line as well
                desc_lines = [text_content]
                if "(" in name:
                    name = name.split("(")[0].strip()

                while i < len(lines):
                    next_line = lines[i].strip()
                    if not next_line:
                        i += 1
                        continue
                    if next_line[0] in "•-*¢" or any(
                        next_line.lower().startswith(kw) for kw in _MOVE_START_KWS
                    ):
                        break

                    if desc_lines:
                        last_line = desc_lines[-1]
                        open_parens = last_line.count("(") - last_line.count(")")
                        if open_parens > 0:
                            desc_lines.append(next_line)
                            i += 1
                            if len(desc_lines) >= 10:
                                break
                            continue

                    break

                desc = " ".join(desc_lines).strip()

            if name and name.strip():
                # Clean up bold markers (** or __) from name
                cleaned_name = name.strip().replace("**", "").replace("__", "").strip()

                # Extract inline metadata from description
                inline_statuses, inline_tags, is_optional, effect_type = (
                    self._extract_inline_move_metadata(desc)
                )

                # Separate custom abilities from GM moves
                if move_type == MoveType.CUSTOM and text_content.startswith("**"):
                    # This is a custom ability - extract trigger if present
                    trigger = ""
                    if desc and desc.lower().startswith("when "):
                        trigger = desc.split(".")[0] if "." in desc else desc
                    custom_abilities.append(
                        CustomAbility(
                            name=cleaned_name,
                            description=(desc.strip() if desc.strip() else cleaned_name),
                            trigger=trigger,
                        )
                    )
                else:
                    # This is a GM move (hard or soft)
                    moves.append(
                        GMMove(
                            name=cleaned_name,
                            description=(desc.strip() if desc.strip() else cleaned_name),
                            move_type=move_type,
                            statuses=inline_statuses,
                            tags=inline_tags,
                            optional=is_optional,
                            effect_type=effect_type,
                        )
                    )
                seen_names.add(text_content.lower())

        return moves, custom_abilities

    def _extract_tags_from_text(self, text: str) -> list[Tag]:
        """Extract tags mentioned in brackets [tag-name] and auto-generate from text."""
        tags = []
        seen_tags = set()

        # First, extract explicit bracket tags
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

        # Auto-generate tags from threat name and keywords
        # Extract threat name keywords (remove common words)
        name_match = self._extract_name(text)
        if name_match and name_match != "Untitled Danger":
            # Replace numbers and make lowercase, split into words
            name_words = re.sub(r"[0-9★⭐]", "", name_match).lower().split()
            for word in name_words:
                word = word.strip("-'").lower()
                # Skip very short or common words
                if len(word) > 2 and word not in {
                    "the",
                    "and",
                    "for",
                    "with",
                    "from",
                    "are",
                    "can",
                    "has",
                    "its",
                }:
                    tag_name = word
                    if tag_name not in seen_tags:
                        tag_type = self._infer_tag_type(tag_name)
                        tags.append(
                            Tag(
                                name=tag_name,
                                tag_type=tag_type,
                            )
                        )
                        seen_tags.add(tag_name)

        # Auto-generate tags from key threat characteristics in description
        description = self._extract_description(text)
        if description:
            desc_lower = description.lower()
            # Look for specific threat keywords
            threat_keywords = {
                "criminal": "threat",
                "underworld": "threat",
                "network": "threat",
                "power": "power",
                "control": "power",
                "violent": "threat",
                "dangerous": "threat",
                "formidable": "threat",
                "ruthless": "threat",
                "empire": "threat",
                "organization": "threat",
            }
            for keyword, inferred_type in threat_keywords.items():
                if keyword in desc_lower and keyword not in seen_tags:
                    tags.append(
                        Tag(
                            name=keyword,
                            tag_type=self._infer_tag_type(inferred_type),
                        )
                    )
                    seen_tags.add(keyword)

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
