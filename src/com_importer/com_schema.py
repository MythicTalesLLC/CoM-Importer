"""
City of Mist Foundry VTT schema definitions.

Defines the data structures for dangers (threats), GM moves, spectrums, tags, and statuses
that align with the City of Mist Foundry module schema.

Reference: https://github.com/taragnor/city-of-mist
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class MoveType(str, Enum):
    """Types of GM moves in City of Mist."""

    SOFT = "soft"
    HARD = "hard"
    CUSTOM = "custom"
    INTRUSION = "intrusion"
    ENTRANCE = "entrance"
    DOWNTIME = "downtime"


class TagType(str, Enum):
    """Types of tags in City of Mist."""

    POWER = "power"
    STORY = "story"
    WEAKNESS = "weakness"
    LOADOUT = "loadout"
    RELATIONSHIP = "relationship"


class TagCategory(str, Enum):
    """Categories for tags representing their mechanical effect."""

    NONE = "none"
    HINDERING = "hindering"
    WEAKENING = "weakening"
    ABILITY = "ability"
    EMPOWER = "empower"
    OBJECT = "object"
    BEING = "being"


class StatusCategory(str, Enum):
    """Categories for status conditions."""

    NONE = "none"
    ADVANCE = "advance"
    HARM = "harm"
    HINDERING = "hindering"
    COMPELLING = "compelling"
    ADVANTAGE = "advantage"
    SHIELD = "shield"
    WEAKENING = "weakening"
    RESTORE = "restore"
    SET_BACK = "set-back"
    PROGRESS = "progress"
    POLAR = "polar"


class SpecialStatusType(str, Enum):
    """Special status types for specific mechanics."""

    COLLECTIVE = "collective"
    EMPTY = ""


@dataclass(frozen=True)
class GMMove:
    """Represents a GM move for a danger/threat."""

    name: str
    description: str
    move_type: MoveType = MoveType.CUSTOM
    tags: list[str] = field(default_factory=list)
    statuses: list[str] = field(default_factory=list)
    hide_name: bool = False
    header: str = "default"  # "default" | "none" | "symbols" | "text"

    def to_foundry_item(self) -> dict[str, Any]:
        """Convert to Foundry item JSON format."""
        return {
            "name": self.name,
            "type": "gmmove",
            "system": {
                "description": self.description,
                "subtype": self.move_type.value,
                "taglist": self.tags,
                "statuslist": self.statuses,
                "hideName": self.hide_name,
                "header": self.header,
                "locked": False,
                "version": "3.0.0",
            },
        }


@dataclass(frozen=True)
class Spectrum:
    """Represents a status spectrum (dual-axis scale) for dangers."""

    name: str
    max_tier: int | None = 4  # Typical spectrum max, can vary; None = immune/unlimited
    current_tier: int = 0
    pips: int = 0

    def to_foundry_item(self) -> dict[str, Any]:
        """Convert to Foundry item JSON format."""
        return {
            "name": self.name,
            "type": "spectrum",
            "system": {
                "maxTier": self.max_tier,
            },
        }


@dataclass(frozen=True)
class Tag:
    """Represents a tag on an actor."""

    name: str
    tag_type: TagType = TagType.POWER
    category: TagCategory = TagCategory.NONE
    description: str = ""
    question: str = ""
    question_letter: str = ""

    def to_foundry_item(self) -> dict[str, Any]:
        """Convert to Foundry item JSON format."""
        return {
            "name": self.name,
            "type": "tag",
            "system": {
                "description": self.description,
                "question": self.question,
                "question_letter": self.question_letter,
                "subtype": self.tag_type.value,
                "category": self.category.value,
                "burn_state": 0,
                "burned": False,
                "crispy": False,
                "is_bonus": False,
                "custom_tag": False,
                "broad": False,
                "temporary": False,
                "permanent": False,
                "locked": False,
                "version": "3.0.0",
            },
        }


@dataclass(frozen=True)
class DangerStatus:
    """Represents a status condition on a danger/threat."""

    name: str
    category: StatusCategory = StatusCategory.NONE
    tier: int = 0
    pips: int = 0
    hidden: bool = False
    temporary: bool = False
    permanent: bool = False
    showcased: bool = False
    special_type: SpecialStatusType = SpecialStatusType.EMPTY
    description: str = ""

    def to_foundry_item(self) -> dict[str, Any]:
        """Convert to Foundry item JSON format."""
        return {
            "name": self.name,
            "type": "status",
            "system": {
                "description": self.description,
                "tier": self.tier,
                "pips": self.pips,
                "category": self.category.value,
                "hidden": self.hidden,
                "temporary": self.temporary,
                "permanent": self.permanent,
                "showcased": self.showcased,
                "specialType": self.special_type.value if self.special_type else "",
                "locked": False,
                "version": "3.0.0",
            },
        }


@dataclass
class DangerActor:
    """Represents a danger/threat actor in Foundry."""

    name: str
    mythos: str = ""
    logos: str = ""
    description: str = ""
    short_description: str = ""
    biography: str = ""
    gmnotes: str = ""
    alias: str = "?????"
    use_alias: bool = True
    locked: bool = False
    is_template: bool = False
    collective_size: int = 0
    finalized: bool = False
    danger_rating: str | None = None
    gm_moves: list[GMMove] = field(default_factory=list)
    spectrums: list[Spectrum] = field(default_factory=list)
    tags: list[Tag] = field(default_factory=list)
    statuses: list[DangerStatus] = field(default_factory=list)

    def validate(self) -> list[str]:
        """Validate the danger has required fields. Returns list of errors."""
        errors = []
        if not self.name or not self.name.strip():
            errors.append("Danger must have a name")
        if not self.description and not self.biography:
            errors.append("Danger must have a description or biography")
        if not self.gm_moves:
            errors.append("Danger should have at least one GM move")
        return errors

    def to_foundry_actor(self, actor_id: str | None = None) -> dict[str, Any]:
        """Convert to Foundry actor JSON format."""
        import uuid

        if actor_id is None:
            actor_id = str(uuid.uuid4())

        # Build items array with all moves, spectrums, tags, statuses
        items: list[dict[str, Any]] = []
        items.extend(move.to_foundry_item() for move in self.gm_moves)
        items.extend(spectrum.to_foundry_item() for spectrum in self.spectrums)
        items.extend(tag.to_foundry_item() for tag in self.tags)
        items.extend(status.to_foundry_item() for status in self.statuses)

        # Build the actor document
        actor = {
            "_id": actor_id,
            "name": self.name,
            "type": "threat",
            "img": "icons/svg/mystery-man.svg",
            "items": items,
            "system": {
                "alias": self.alias,
                "useAlias": self.use_alias,
                "biography": self.biography,
                "description": self.description,
                "short_description": self.short_description,
                "gmnotes": self.gmnotes,
                "mythos": self.mythos,
                "logos": self.logos,
                "locked": self.locked,
                "is_template": self.is_template,
                "collective_size": self.collective_size,
                "finalized": self.finalized,
                "crewThemes": [],
                "version": "3.0.0",
            },
            "prototypeToken": {
                "name": self.name,
                "displayName": 10,  # Hover
                "actorLink": False,
                "appendNumber": False,
                "prependAdjective": False,
                "texture": {
                    "src": "icons/svg/mystery-man.svg",
                },
                "width": 1,
                "height": 1,
            },
        }

        return actor


@dataclass
class Theme:
    """Represents an active theme on a player character."""

    name: str  # "Mythos", "Logos", "Mist", or custom
    description: str = ""
    tags: list[Tag] = field(default_factory=list)
    improvements: list[str] = field(default_factory=list)

    def to_foundry_item(self) -> dict[str, Any]:
        """Convert to Foundry themekit item JSON format."""
        items: list[dict[str, Any]] = [tag.to_foundry_item() for tag in self.tags]
        return {
            "name": self.name,
            "type": "themekit",
            "items": items,
            "system": {
                "description": self.description,
                "improvements": self.improvements,
                "locked": False,
                "version": "3.0.0",
            },
        }


@dataclass
class CharacterActor:
    """Represents a player character actor in Foundry."""

    name: str
    pronouns: str = ""
    description: str = ""
    biography: str = ""
    gmnotes: str = ""
    locked: bool = False
    themes: list[Theme] = field(default_factory=list)
    juice_help: int = 0
    juice_hurt: int = 0
    crew_id: str | None = None

    def validate(self) -> list[str]:
        """Validate the character has required fields. Returns list of errors."""
        errors = []
        if not self.name or not self.name.strip():
            errors.append("Character must have a name")
        if not self.themes:
            errors.append("Character should have at least one theme")
        return errors

    def to_foundry_actor(self, actor_id: str | None = None) -> dict[str, Any]:
        """Convert to Foundry actor JSON format."""
        import uuid

        if actor_id is None:
            actor_id = str(uuid.uuid4())

        # Build items array with themes containing tags
        items: list[dict[str, Any]] = [theme.to_foundry_item() for theme in self.themes]

        # Build the actor document
        actor = {
            "_id": actor_id,
            "name": self.name,
            "type": "character",
            "img": "icons/svg/mystery-man.svg",
            "items": items,
            "system": {
                "biography": self.biography,
                "description": self.description,
                "gmnotes": self.gmnotes,
                "pronouns": self.pronouns,
                "locked": self.locked,
                "crewThemes": [self.crew_id] if self.crew_id else [],
                "juice": {
                    "help": self.juice_help,
                    "hurt": self.juice_hurt,
                },
                "version": "3.0.0",
            },
            "prototypeToken": {
                "name": self.name,
                "displayName": 10,  # Hover
                "actorLink": True,  # PCs are usually linked to tokens
                "appendNumber": False,
                "prependAdjective": False,
                "texture": {
                    "src": "icons/svg/mystery-man.svg",
                },
                "width": 1,
                "height": 1,
            },
        }

        return actor


def schema_from_dict(data: dict[str, Any]) -> DangerActor:
    """Create a DangerActor from a dictionary (lossy conversion - best effort)."""
    gm_moves = []
    spectrums = []
    tags = []
    statuses = []

    # This is a utility for basic conversions; full schema mapping happens elsewhere
    return DangerActor(
        name=data.get("name", ""),
        mythos=data.get("mythos", ""),
        logos=data.get("logos", ""),
        description=data.get("description", ""),
        short_description=data.get("short_description", ""),
        biography=data.get("biography", ""),
        gmnotes=data.get("gmnotes", ""),
        alias=data.get("alias", "?????"),
        use_alias=data.get("use_alias", True),
        locked=data.get("locked", False),
        is_template=data.get("is_template", False),
        collective_size=data.get("collective_size", 0),
        finalized=data.get("finalized", False),
        danger_rating=data.get("danger_rating"),
        gm_moves=gm_moves,
        spectrums=spectrums,
        tags=tags,
        statuses=statuses,
    )
