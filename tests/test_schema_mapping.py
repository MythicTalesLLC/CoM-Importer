"""
Tests for the new schema mapping features:
- Spectrum line detection and parsing (all formats)
- Collective/Vehicle/Team extraction
- Inline status/story tag extraction from move descriptions
- Mythos Power Set detection
- GMMove optional + effect_type flags
"""

from com_importer.com_schema import DangerActor, GMMove, MoveType
from com_importer.danger_parser import DangerParser


class TestSpectrumParsing:
    """Test spectrum extraction in all rulebook formats."""

    def setup_method(self):
        self.parser = DangerParser()

    def test_slash_format_standard(self):
        """'Name: current/max' format."""
        text = "Threat\nHealth: 2/4\n• Do something"
        d, _ = self.parser.parse(text)
        names = {s.name for s in d.spectrums}
        assert "Health" in names
        sp = next(s for s in d.spectrums if s.name == "Health")
        assert sp.max_tier == 4
        assert sp.current_tier == 2

    def test_allcaps_slash_format(self):
        """'GET INTO TROUBLE 3 / HURT OR SUBDUE 4' format."""
        text = "Corrupt Cop\nGET INTO TROUBLE 3 / HURT OR SUBDUE 4\n• Use the system (hard move)"
        d, _ = self.parser.parse(text)
        names = {s.name for s in d.spectrums}
        assert "GET INTO TROUBLE" in names
        assert "HURT OR SUBDUE" in names

    def test_allcaps_space_separated(self):
        """'CORRUPT 3 BRIBE -' space-separated format."""
        text = "Corp Lawyer\nCORRUPT 3 BRIBE -\n• Threaten lawsuit"
        d, _ = self.parser.parse(text)
        names = {s.name for s in d.spectrums}
        assert "CORRUPT" in names
        c = next(s for s in d.spectrums if s.name == "CORRUPT")
        assert c.max_tier == 3
        # BRIBE - means unlimited/immune
        assert "BRIBE" in names
        b = next(s for s in d.spectrums if s.name == "BRIBE")
        assert b.max_tier is None

    def test_dash_means_null(self):
        """Dash value means immune/unlimited → max_tier=None."""
        text = "Iron Wall\nHURT OR SUBDUE -\n• Slam"
        d, _ = self.parser.parse(text)
        s = next((sp for sp in d.spectrums if sp.name == "HURT OR SUBDUE"), None)
        assert s is not None
        assert s.max_tier is None

    def test_explicit_spectrum_section(self):
        """Explicit 'Spectrum:' header with Name: x/y lines beneath."""
        text = (
            "The Darkness\n"
            "Description paragraph.\n"
            "Spectrum:\n"
            "Fear: 0/3\n"
            "Sanity: 1/5\n"
            "• Creep in the shadows"
        )
        d, _ = self.parser.parse(text)
        names = {s.name for s in d.spectrums}
        assert "Fear" in names
        assert "Sanity" in names

    def test_four_spectrums(self):
        """Up to 4 spectrums can appear."""
        text = "Big Boss\n" "HURT OR SUBDUE 3 / CORRUPT 4\n" "SCARE 2 / THREATEN -\n" "• Hard move"
        d, _ = self.parser.parse(text)
        assert len(d.spectrums) == 4

    def test_no_spectrum_for_mythos_power_set(self):
        """Mythos Power Sets have no spectrum line."""
        text = "Ancient Horror +★★\n• Drive insane (hard move)"
        d, _ = self.parser.parse(text)
        assert d.spectrums == []
        assert d.is_mythos_power_set is True


class TestCollectiveExtraction:
    """Test Collective/Vehicle/Team note extraction."""

    def setup_method(self):
        self.parser = DangerParser()

    def test_collective_with_size(self):
        text = (
            "Street Mob\n"
            "A group of angry criminals.\n"
            "HURT OR SUBDUE 3\n"
            "Collective: This collective has 10 members...\n"
            "• Overwhelm"
        )
        d, _ = self.parser.parse(text)
        assert d.collective_note != ""
        assert d.collective_size == 10

    def test_vehicle_note(self):
        text = (
            "War Truck\n"
            "A heavily armoured vehicle.\n"
            "HURT OR SUBDUE 4\n"
            "Vehicle: Armoured personnel carrier, 4 wheels\n"
            "• Ram (hard move)"
        )
        d, _ = self.parser.parse(text)
        assert d.collective_note != ""
        assert "Armoured" in d.collective_note or "personnel" in d.collective_note.lower()

    def test_no_collective(self):
        text = "Solo\nA lone figure.\nHURT OR SUBDUE 3\n• Strike"
        d, _ = self.parser.parse(text)
        assert d.collective_size == 0
        assert d.collective_note == ""


class TestInlineMoveMetadata:
    """Test extraction of (status-N), (story tag), (optional), and createDanger flags."""

    def setup_method(self):
        self.parser = DangerParser()

    def test_status_in_parens_extracted(self):
        text = "Lawyer\nCORRUPT 3\n" "• Use the court system (legal-trouble-3)"
        d, _ = self.parser.parse(text)
        assert d.gm_moves, "Expected at least one GM move"
        move = d.gm_moves[0]
        assert "legal-trouble-3" in move.statuses

    def test_story_tag_in_parens_extracted(self):
        text = "Ghost\nHURT OR SUBDUE 3\n" "• Pass through walls (temporary)"
        d, _ = self.parser.parse(text)
        assert d.gm_moves
        move = d.gm_moves[0]
        assert "temporary" in move.tags

    def test_optional_flag(self):
        text = "Mystic\nHURT OR SUBDUE 2\n" "• Vanish into thin air (optional)"
        d, _ = self.parser.parse(text)
        assert d.gm_moves
        move = d.gm_moves[0]
        assert move.optional is True

    def test_create_danger_effect(self):
        text = (
            "Summoner\nHURT OR SUBDUE 3\n"
            "• Call reinforcements: create a new Danger from the shadows"
        )
        d, _ = self.parser.parse(text)
        assert d.gm_moves
        move = d.gm_moves[0]
        assert move.effect_type == "createDanger"

    def test_deny_them_effect(self):
        text = "Blocker\nHURT OR SUBDUE 3\n" "• Block escape: Deny Them Something They Want"
        d, _ = self.parser.parse(text)
        assert d.gm_moves
        move = d.gm_moves[0]
        assert move.effect_type == "special"


class TestMythosPowerSet:
    """Test Mythos Power Set detection."""

    def setup_method(self):
        self.parser = DangerParser()

    def test_additive_star_rating_detected(self):
        text = "Ancient Curse +★★\n• Inflict madness (hard move)"
        d, _ = self.parser.parse(text)
        assert d.is_mythos_power_set is True
        assert d.danger_rating is not None
        assert d.danger_rating.startswith("+")

    def test_normal_threat_not_mythos_power_set(self):
        text = "Street Thug ★★\nHURT OR SUBDUE 2\n• Punch"
        d, _ = self.parser.parse(text)
        assert d.is_mythos_power_set is False


class TestGMMoveFoundryOutput:
    """Test that GMMove optional/effect_type fields appear in Foundry JSON."""

    def test_optional_in_foundry_item(self):
        move = GMMove(
            name="Vanish",
            description="Disappear",
            move_type=MoveType.SOFT,
            optional=True,
        )
        item = move.to_foundry_item()
        assert item["system"].get("optional") is True

    def test_effect_type_in_foundry_item(self):
        move = GMMove(
            name="Summon",
            description="Create a new Danger",
            move_type=MoveType.SOFT,
            effect_type="createDanger",
        )
        item = move.to_foundry_item()
        assert item["system"].get("effectType") == "createDanger"

    def test_no_optional_key_when_false(self):
        move = GMMove(name="Strike", description="Hit", move_type=MoveType.HARD)
        item = move.to_foundry_item()
        # optional=False should not pollute the output
        assert "optional" not in item["system"]

    def test_no_effect_type_key_when_empty(self):
        move = GMMove(name="Strike", description="Hit", move_type=MoveType.HARD)
        item = move.to_foundry_item()
        assert "effectType" not in item["system"]


class TestCollectiveInFoundry:
    """Test collective_note and collective_size propagate to Foundry JSON."""

    def test_collective_fields_in_actor(self):
        from com_importer.danger_to_foundry import convert_danger_to_foundry

        danger = DangerActor(
            name="Street Mob",
            description="Many criminals",
            collective_size=5,
            collective_note="A dangerous collective",
            gm_moves=[GMMove(name="Swarm", description="Overwhelm", move_type=MoveType.SOFT)],
        )
        actor = convert_danger_to_foundry(danger)
        assert actor["system"]["collective_size"] == 5
        assert actor["system"]["collective_note"] == "A dangerous collective"
