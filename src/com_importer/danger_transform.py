"""
Text transformation and normalization for danger descriptions.

Cleans up pasted text, handles OCR artifacts, and prepares text for parsing.
"""

from __future__ import annotations

import re


def normalize_danger_text(text: str) -> str:
    """
    Normalize danger text for parsing.

    Handles:
    - Extra whitespace
    - Common OCR artifacts
    - Line breaks within words
    - Inconsistent formatting

    Args:
        text: Raw text to normalize

    Returns:
        Normalized text
    """
    # Strip leading/trailing whitespace
    text = text.strip()

    # Fix common OCR issues
    text = _fix_ocr_artifacts(text)

    # Normalize line breaks (remove soft breaks within paragraphs)
    text = _normalize_line_breaks(text)

    # Clean up multiple spaces
    text = re.sub(r" +", " ", text)

    # Clean up unicode issues
    text = _fix_unicode_issues(text)

    return text


def _fix_ocr_artifacts(text: str) -> str:
    """Fix common OCR misreadings."""
    replacements = {
        r"\b0\b": "O",  # Zero sometimes read as O
        r"\b1\b": "I",  # One sometimes read as I
        r"\b[l1]\b": "l",  # Inconsistent letter L
        "rn": "m",  # Common OCR confusion (context-dependent)
        "vvhat": "what",
        "vvill": "will",
        "vvhen": "when",
    }

    for pattern, replacement in replacements.items():
        text = re.sub(pattern, replacement, text)

    # Fix known City of Mist terms that might be misread
    com_terms_fixes = {
        r"Mythos": "Mythos",
        r"Logos": "Logos",
        r"Spectrum": "Spectrum",
        r"Theme": "Theme",
        r"Tag": "Tag",
        r"Status": "Status",
    }

    for term, correct in com_terms_fixes.items():
        # Case-insensitive replacement (do NOT lowercase the entire text)
        text = re.sub(term, correct, text, flags=re.IGNORECASE)

    return text


def _normalize_line_breaks(text: str) -> str:
    """
    Normalize line breaks.

    Preserves paragraph breaks (double newlines) and bullet-point lines.
    Merges only soft-wrapped continuation lines (no bullet at start).
    """
    # Preserve paragraph breaks
    paragraphs = re.split(r"\n{2,}", text)

    normalized_paragraphs = []
    for para in paragraphs:
        lines = para.split("\n")
        result_lines: list[str] = []
        current = ""
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            # Lines starting with a bullet char start a new item — flush current
            if stripped[0] in "•-*¢":
                if current:
                    result_lines.append(current)
                current = stripped
            else:
                # Soft-wrapped continuation — append to current
                current = (current + " " + stripped).strip() if current else stripped
        if current:
            result_lines.append(current)
        if result_lines:
            normalized_paragraphs.append("\n".join(result_lines))

    return "\n\n".join(normalized_paragraphs)


def _fix_unicode_issues(text: str) -> str:
    """Fix common unicode problems."""
    replacements = {
        """: '"',  # Fancy left quote
        """: '"',  # Fancy right quote
        "'": "'",  # Fancy single quote
        "—": "-",  # Em dash
        "–": "-",  # En dash
        "…": "...",  # Ellipsis
    }

    for fancy, simple in replacements.items():
        text = text.replace(fancy, simple)

    return text


def extract_sections(
    text: str,
) -> dict[str, str]:
    """
    Extract major sections from danger text.

    Returns a dict with keys like:
    - header: Name and rating
    - description: Main description
    - spectrums: Spectrum section
    - moves: GM moves section
    - other: Everything else

    Args:
        text: Normalized danger text

    Returns:
        Dictionary of sections
    """
    sections = {
        "header": "",
        "description": "",
        "spectrums": "",
        "moves": "",
        "other": "",
    }

    # Split on major section headers
    # Common headers: "Spectrum", "Hard Move", "Soft Move", "Custom Move"

    # Extract header (first section before any keywords)
    header_end = min(
        (
            m.start()
            for m in re.finditer(
                r"\n(?:mythos|logos|spectrum|move|rating)",
                text.lower(),
            )
            if m
        ),
        default=len(text),
    )
    if header_end > 0:
        sections["header"] = text[:header_end].strip()
        text = text[header_end:].strip()

    # Now split remaining text on major sections
    remaining_sections = re.split(
        r"\n(?:status\s+)?spectrum[:\s]*",
        text,
        maxsplit=1,
        flags=re.IGNORECASE,
    )
    if len(remaining_sections) > 1:
        sections["description"] = remaining_sections[0].strip()
        text = remaining_sections[1].strip()
    else:
        sections["description"] = text.strip()
        return sections

    # Extract spectrums
    spectrum_match = re.match(
        r"(.+?)(?=\n(?:hard|soft|custom|when))",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if spectrum_match:
        sections["spectrums"] = spectrum_match.group(1).strip()
        text = text[spectrum_match.end() :].strip()

    # Extract moves
    move_match = re.match(
        r"(.+?)(?=\ntags?|\Z)",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if move_match:
        sections["moves"] = move_match.group(1).strip()
        text = text[move_match.end() :].strip()

    # Everything else
    sections["other"] = text.strip()

    return sections


def clean_field_value(
    value: str,
    field_type: str = "text",
) -> str:
    """
    Clean a field value for consistency.

    Args:
        value: The value to clean
        field_type: Type of field (text, number, list, etc.)

    Returns:
        Cleaned value
    """
    if not value:
        return ""

    value = value.strip()

    if field_type == "number":
        # Extract first number
        match = re.search(r"\d+", value)
        return match.group(0) if match else ""

    if field_type == "list":
        # Split on common delimiters and clean
        items = re.split(r"[,;]", value)
        return ", ".join(item.strip() for item in items if item.strip())

    return value
