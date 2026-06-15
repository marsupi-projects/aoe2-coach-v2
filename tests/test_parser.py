"""
Tests for core/parser.py.

Covers both single-line and multi-line player block formats that Claude may
produce, plus the derived flags (has_team_synergy, has_data_limitations) and
emoji stripping in the result field.
"""

import pytest
from core.parser import extract_report


# ---------------------------------------------------------------------------
# Sample report fixtures
# ---------------------------------------------------------------------------

REPORT_MULTILINE = """\
==============================================================
  AGE OF EMPIRES II - COACHING REPORT
==============================================================

DATA LIMITATIONS
----------------
This is a vs-AI game so feudal and castle timings are not available.
----------------

GAME OVERVIEW
-------------

==============================================================
  PLAYER 1 - dreas.kesbeke
==============================================================

  Civilisation : Byzantines
  eAPM         : 16
  Result       : Win

  HISTORICAL CONTEXT
  No previous games on record for dreas.kesbeke.

  OBSERVATIONS
  1. Steady eAPM for a team game.

  RECOMMENDATIONS
  1. Push aggression earlier.

==============================================================
  PLAYER 2 - walter2515
==============================================================

  Civilisation : Aztecs
  eAPM         : 24
  Result       : Win

  HISTORICAL CONTEXT
  Previous game: Byzantines on Arabia (Win).

  OBSERVATIONS
  1. Strong micro with infantry.

  RECOMMENDATIONS
  1. Add monks to the army composition.

==============================================================
  TEAM SYNERGY - dreas.kesbeke + walter2515
==============================================================

Byzantine + Aztec: complementary defensive and rush potential.
"""

REPORT_INLINE = """\
PLAYER: dreas.kesbeke | Byzantines | eAPM: 16 | Result: Win
PLAYER: walter2515 | Aztecs | eAPM: 24 | Result: Loss

HISTORICAL CONTEXT - no previous games on record for either player.

TEAM SYNERGY - brief mention.

DATA LIMITATIONS - vs-AI game.
"""

REPORT_EMOJI = """\
==============================================================
  PLAYER 1 - Alice
==============================================================

  Civilisation : Britons
  eAPM         : 55
  Result       : ✅ Win

==============================================================
  PLAYER 2 - Bob
==============================================================

  Civilisation : Franks
  eAPM         : 38
  Result       : ❌ Loss
"""

REPORT_CIVILIZATION_SPELLING = """\
==============================================================
  PLAYER 1 - Alice
==============================================================

  Civilization : Britons
  eAPM         : 55
  Result       : Win
"""

REPORT_SOLO = """\
==============================================================
  PLAYER 1 - Alice
==============================================================

  Civilisation : Britons
  eAPM         : 55
  Result       : Win

  HISTORICAL CONTEXT
  No previous games on record.
"""


# ---------------------------------------------------------------------------
# Multi-line format
# ---------------------------------------------------------------------------

class TestMultilineFormat:
    def test_player_count(self):
        result = extract_report(REPORT_MULTILINE)
        assert len(result["players"]) == 2

    def test_player1_name(self):
        p = extract_report(REPORT_MULTILINE)["players"][0]
        assert p["name"] == "dreas.kesbeke"

    def test_player1_civ(self):
        p = extract_report(REPORT_MULTILINE)["players"][0]
        assert p["civ"] == "Byzantines"

    def test_player1_eapm(self):
        p = extract_report(REPORT_MULTILINE)["players"][0]
        assert p["eapm"] == 16

    def test_player1_result(self):
        p = extract_report(REPORT_MULTILINE)["players"][0]
        assert p["result"] == "Win"

    def test_player2_name(self):
        p = extract_report(REPORT_MULTILINE)["players"][1]
        assert p["name"] == "walter2515"

    def test_player2_civ(self):
        p = extract_report(REPORT_MULTILINE)["players"][1]
        assert p["civ"] == "Aztecs"

    def test_player2_eapm(self):
        p = extract_report(REPORT_MULTILINE)["players"][1]
        assert p["eapm"] == 24

    def test_has_team_synergy(self):
        assert extract_report(REPORT_MULTILINE)["has_team_synergy"] is True

    def test_has_data_limitations(self):
        assert extract_report(REPORT_MULTILINE)["has_data_limitations"] is True

    def test_raw_preserved(self):
        result = extract_report(REPORT_MULTILINE)
        assert "Byzantines" in result["raw"]


# ---------------------------------------------------------------------------
# Single-line (inline) format
# ---------------------------------------------------------------------------

class TestInlineFormat:
    def test_player_count(self):
        assert len(extract_report(REPORT_INLINE)["players"]) == 2

    def test_player1_fields(self):
        p = extract_report(REPORT_INLINE)["players"][0]
        assert p["name"] == "dreas.kesbeke"
        assert p["civ"] == "Byzantines"
        assert p["eapm"] == 16
        assert p["result"] == "Win"

    def test_player2_result(self):
        p = extract_report(REPORT_INLINE)["players"][1]
        assert p["result"] == "Loss"

    def test_has_team_synergy(self):
        assert extract_report(REPORT_INLINE)["has_team_synergy"] is True

    def test_has_data_limitations(self):
        assert extract_report(REPORT_INLINE)["has_data_limitations"] is True


# ---------------------------------------------------------------------------
# Emoji stripping in result field
# ---------------------------------------------------------------------------

class TestEmojiStripping:
    def test_checkmark_win(self):
        p = extract_report(REPORT_EMOJI)["players"][0]
        assert p["result"] == "Win"

    def test_cross_loss(self):
        p = extract_report(REPORT_EMOJI)["players"][1]
        assert p["result"] == "Loss"


# ---------------------------------------------------------------------------
# "Civilization" (American) spelling variant
# ---------------------------------------------------------------------------

class TestCivilizationSpelling:
    def test_american_spelling_parsed(self):
        p = extract_report(REPORT_CIVILIZATION_SPELLING)["players"][0]
        assert p["civ"] == "Britons"


# ---------------------------------------------------------------------------
# Flags: has_team_synergy and has_data_limitations
# ---------------------------------------------------------------------------

class TestFlags:
    def test_no_team_synergy_when_section_absent(self):
        assert extract_report(REPORT_SOLO)["has_team_synergy"] is False

    def test_no_data_limitations_when_section_absent(self):
        assert extract_report(REPORT_SOLO)["has_data_limitations"] is False

    def test_team_synergy_case_insensitive(self):
        result = extract_report("team synergy section here")
        assert result["has_team_synergy"] is True

    def test_data_limitations_case_insensitive(self):
        result = extract_report("data limitations noted below")
        assert result["has_data_limitations"] is True


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_empty_string(self):
        result = extract_report("")
        assert result["players"] == []
        assert result["has_team_synergy"] is False
        assert result["has_data_limitations"] is False

    def test_no_player_blocks(self):
        result = extract_report("This report has no player sections at all.")
        assert result["players"] == []

    def test_raw_is_stripped(self):
        result = extract_report("  hello  ")
        assert result["raw"] == "hello"
