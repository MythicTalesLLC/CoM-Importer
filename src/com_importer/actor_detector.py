"""Auto-detect actor type (danger/threat vs character) from text content."""

from __future__ import annotations


class ActorTypeDetector:
    """Detect whether text describes a threat/danger or player character."""

    THREAT_INDICATORS = [
        "FOOL",  # Threat stat
        "SCARE",  # Threat stat
        "Hard Move",  # Threat ability
        "Soft Move",  # Threat ability
        "Custom Move",  # Threat ability
        "Danger Rating",  # Threat descriptor
        "Spectrum",  # Threat only (characters don't have spectrums)
    ]

    CHARACTER_INDICATORS = [
        "Mythos:",  # Character theme (with colon showing description)
        "Logos:",  # Character theme (with colon)
        "Mist:",  # Character theme (with colon)
        "Juice:",  # Character juice tracking
        "help",  # Part of "help X/X" in juice
        "hurt",  # Part of "hurt X/X" in juice
        "Pronouns:",  # Character field
        "She/",  # Pronoun
        "He/",  # Pronoun
        "They/",  # Pronoun
    ]

    @staticmethod
    def detect(text: str) -> str:
        """
        Detect actor type from text content.

        Args:
            text: Actor description text

        Returns:
            "danger" (threat/NPC) or "character" (player character)
        """
        text_lower = text.lower()

        # Count indicators
        threat_count = sum(
            1 for ind in ActorTypeDetector.THREAT_INDICATORS if ind.lower() in text_lower
        )
        char_count = sum(
            1 for ind in ActorTypeDetector.CHARACTER_INDICATORS if ind.lower() in text_lower
        )

        # Determine type based on indicators
        if threat_count > char_count:
            return "danger"
        elif char_count > threat_count:
            return "character"
        else:
            # When tied or both zero, default to danger (more common in CoM)
            # unless we see strong character indicators
            if char_count > 0:
                return "character"
            return "danger"

    @staticmethod
    def confidence(text: str) -> dict[str, float]:
        """
        Get confidence scores for both actor types.

        Args:
            text: Actor description text

        Returns:
            Dict with "danger" and "character" confidence scores (0.0 to 1.0)
        """
        text_lower = text.lower()

        threat_count = sum(
            1 for ind in ActorTypeDetector.THREAT_INDICATORS if ind.lower() in text_lower
        )
        char_count = sum(
            1 for ind in ActorTypeDetector.CHARACTER_INDICATORS if ind.lower() in text_lower
        )

        total = threat_count + char_count
        if total == 0:
            return {"danger": 0.5, "character": 0.5}

        return {"danger": threat_count / total, "character": char_count / total}
