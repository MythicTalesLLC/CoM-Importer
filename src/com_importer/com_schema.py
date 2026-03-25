"""
City of Mist Foundry VTT schema definitions.

Defines the data structures for dangers (threats), GM moves, spectrums, tags, and statuses
that align with the City of Mist Foundry module schema.

Reference: https://github.com/MythicTalesLLC/city-of-mist-custom
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
    CHOICES = "choices"  # Preamble / aggregator text preceding a list of hard or soft moves
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
    optional: bool = False  # Move is marked (optional) in rulebook
    effect_type: str = ""  # "createDanger", "special", or ""

    def to_foundry_item(self) -> dict[str, Any]:
        """Convert to Foundry item JSON format."""
        # "choices" is an aggregator/preamble — Foundry doesn't know this type, so
        # output as soft with the name hidden so only the description (the choice text) shows.
        foundry_subtype = "soft" if self.move_type == MoveType.CHOICES else self.move_type.value
        system: dict[str, Any] = {
            "description": self.description,
            "subtype": foundry_subtype,
            "taglist": self.tags,
            "statuslist": self.statuses,
            "hideName": self.hide_name or (self.move_type == MoveType.CHOICES),
            "header": self.header,
            "locked": False,
            "version": "3.0.0",
        }
        if self.optional:
            system["optional"] = True
        if self.effect_type:
            system["effectType"] = self.effect_type
        return {
            "name": self.name or "(choices)",
            "type": "gmmove",
            "system": system,
        }


@dataclass(frozen=True)
class CustomAbility:
    """Represents a custom ability (special rule) for a danger/threat.

    Custom abilities are formatted as **Name:** description in the rulebook.
    They define special triggered effects or rules unique to the danger.
    """

    name: str
    description: str
    trigger: str = ""  # Optional trigger condition (e.g., "When you...")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format for system.customAbilities."""
        return {
            "name": self.name,
            "description": self.description,
            "trigger": self.trigger,
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
        # Map TagType to CoM4 category values
        if self.category != TagCategory.NONE:
            category_val = self.category.value
        elif self.tag_type == TagType.POWER:
            category_val = "ability"
        elif self.tag_type == TagType.WEAKNESS:
            category_val = "hindering"
        else:
            category_val = "none"

        return {
            "name": self.name,
            "type": "tag",
            "img": "icons/svg/item-bag.svg",
            "system": {
                "description": self.description,
                "question": self.question,
                "question_letter": self.question_letter,
                "subtype": self.tag_type.value,
                "category": category_val,
                "burn_state": 0,
                "burned": False,
                "crispy": False,
                "is_bonus": False,
                "custom_tag": False,
                "broad": False,
                "temporary": False,
                "permanent": False,
                "locked": False,
                "version": "1",
                "parentId": None,
                "subtagRequired": False,
                "showcased": False,
                "activated_loadout": False,
                "sceneId": None,
                "createdBy": [],
                "example0": "",
                "example1": "",
                "example2": "",
                "counterexample0": "",
                "counterexample1": "",
                "counterexample2": "",
                "restriction0": "",
                "restriction1": "",
                "restriction2": "",
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
    collective_note: str = ""  # Collective/Vehicle/Team descriptor from rulebook
    finalized: bool = False
    danger_rating: str | None = None
    is_mythos_power_set: bool = False  # Additive +★ rating, no spectrum line
    gm_moves: list[GMMove] = field(default_factory=list)
    custom_abilities: list[CustomAbility] = field(default_factory=list)
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
        import random
        import string

        def _fid() -> str:
            return "".join(random.choices(string.ascii_letters + string.digits, k=16))

        if actor_id is None:
            actor_id = _fid()

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
                "collective_note": self.collective_note,
                "finalized": self.finalized,
                "customAbilities": [ability.to_dict() for ability in self.custom_abilities],
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
        collective_note=data.get("collective_note", ""),
        finalized=data.get("finalized", False),
        danger_rating=data.get("danger_rating"),
        is_mythos_power_set=data.get("is_mythos_power_set", False),
        gm_moves=gm_moves,
        spectrums=spectrums,
        tags=tags,
        statuses=statuses,
    )
