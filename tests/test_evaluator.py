"""
Tests for core/evaluator.py.

Covers all 11 SPEC.md §3 criteria individually, score calculation, and the
pass threshold. Uses minimal synthetic inputs — no ChromaDB or API calls needed.
"""

import pytest
from core.evaluator import evaluate


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------

def make_parsed_data(
    players=None,
    limited_data=False,
):
    if players is None:
        players = [
            {
                "name": "dreas.kesbeke",
                "civ": "Byzantines",
                "civ_id": 3,
                "is_human": True,
                "team": 1,
                "winner": True,
                "eapm": 16,
            },
            {
                "name": "walter2515",
                "civ": "Aztecs",
                "civ_id": 1,
                "is_human": True,
                "team": 1,
                "winner": True,
                "eapm": 24,
            },
        ]
    return {
        "players": players,
        "map_name": "Black Forest",
        "game_type": "Random Map",
        "completed": True,
        "limited_data": limited_data,
        "note": "",
    }


def make_parsed_report(
    players=None,
    has_team_synergy=True,
    has_data_limitations=False,
    raw=None,
):
    if players is None:
        players = [
            {"name": "dreas.kesbeke", "civ": "Byzantines", "eapm": 16, "result": "Win"},
            {"name": "walter2515", "civ": "Aztecs", "eapm": 24, "result": "Win"},
        ]
    if raw is None:
        raw = (
            "HISTORICAL CONTEXT\n"
            "No previous games on record for dreas.kesbeke.\n"
            "No previous games on record for walter2515.\n"
            "TEAM SYNERGY - good combo.\n"
            "Some more content to pass the 200-char length check. " * 5
        )
    return {
        "raw": raw,
        "players": players,
        "has_team_synergy": has_team_synergy,
        "has_data_limitations": has_data_limitations,
    }


def make_run_meta(
    report_path_exists=True,
    run_entry_written=True,
    chroma_stored=True,
    elapsed_seconds=200.0,
):
    return {
        "report_path_exists": report_path_exists,
        "run_entry_written": run_entry_written,
        "chroma_stored": chroma_stored,
        "elapsed_seconds": elapsed_seconds,
    }


def get_criterion(result, name):
    return next(c for c in result["criteria"] if c["name"] == name)


# ---------------------------------------------------------------------------
# Full-pass baseline
# ---------------------------------------------------------------------------

class TestFullPass:
    def test_score_is_1(self):
        r = evaluate(make_parsed_data(), make_parsed_report(), make_run_meta())
        assert r["score"] == 1.0

    def test_passed_true(self):
        r = evaluate(make_parsed_data(), make_parsed_report(), make_run_meta())
        assert r["passed"] is True

    def test_11_criteria_returned(self):
        r = evaluate(make_parsed_data(), make_parsed_report(), make_run_meta())
        assert len(r["criteria"]) == 11

    def test_all_criteria_passed(self):
        r = evaluate(make_parsed_data(), make_parsed_report(), make_run_meta())
        failing = [c for c in r["criteria"] if not c["passed"]]
        assert failing == []


# ---------------------------------------------------------------------------
# C1 — replay_parsed
# ---------------------------------------------------------------------------

class TestC1ReplayParsed:
    def test_fails_on_empty_dict(self):
        r = evaluate({}, make_parsed_report(), make_run_meta())
        assert get_criterion(r, "replay_parsed")["passed"] is False

    def test_fails_on_missing_players_key(self):
        r = evaluate({"map_name": "Arabia"}, make_parsed_report(), make_run_meta())
        assert get_criterion(r, "replay_parsed")["passed"] is False

    def test_passes_with_valid_data(self):
        r = evaluate(make_parsed_data(), make_parsed_report(), make_run_meta())
        assert get_criterion(r, "replay_parsed")["passed"] is True


# ---------------------------------------------------------------------------
# C2 — human_players_identified
# ---------------------------------------------------------------------------

class TestC2HumanPlayers:
    def test_fails_when_no_human_players(self):
        ai_only = make_parsed_data(players=[
            {"name": "", "civ": "Teutons", "civ_id": 4, "is_human": False,
             "team": 2, "winner": False, "eapm": 200},
        ])
        r = evaluate(ai_only, make_parsed_report(), make_run_meta())
        assert get_criterion(r, "human_players_identified")["passed"] is False

    def test_passes_with_one_human(self):
        solo = make_parsed_data(players=[
            {"name": "Alice", "civ": "Britons", "civ_id": 0, "is_human": True,
             "team": 1, "winner": True, "eapm": 40},
        ])
        r = evaluate(solo, make_parsed_report(), make_run_meta())
        assert get_criterion(r, "human_players_identified")["passed"] is True


# ---------------------------------------------------------------------------
# C3 — all_players_covered
# ---------------------------------------------------------------------------

class TestC3AllPlayersCovered:
    def test_fails_when_player_missing(self):
        report_missing_one = make_parsed_report(players=[
            {"name": "dreas.kesbeke", "civ": "Byzantines", "eapm": 16, "result": "Win"},
            # walter2515 missing
        ])
        r = evaluate(make_parsed_data(), report_missing_one, make_run_meta())
        assert get_criterion(r, "all_players_covered")["passed"] is False

    def test_passes_when_all_covered(self):
        r = evaluate(make_parsed_data(), make_parsed_report(), make_run_meta())
        assert get_criterion(r, "all_players_covered")["passed"] is True

    def test_name_match_is_case_insensitive(self):
        report_upper = make_parsed_report(players=[
            {"name": "DREAS.KESBEKE", "civ": "Byzantines", "eapm": 16, "result": "Win"},
            {"name": "WALTER2515", "civ": "Aztecs", "eapm": 24, "result": "Win"},
        ])
        r = evaluate(make_parsed_data(), report_upper, make_run_meta())
        assert get_criterion(r, "all_players_covered")["passed"] is True


# ---------------------------------------------------------------------------
# C4 — civ_names_resolved
# ---------------------------------------------------------------------------

class TestC4CivNamesResolved:
    def test_fails_on_raw_civ_id(self):
        report = make_parsed_report(raw="The player used civ_7 in this game. " * 10)
        r = evaluate(make_parsed_data(), report, make_run_meta())
        assert get_criterion(r, "civ_names_resolved")["passed"] is False

    def test_passes_with_named_civs(self):
        r = evaluate(make_parsed_data(), make_parsed_report(), make_run_meta())
        assert get_criterion(r, "civ_names_resolved")["passed"] is True


# ---------------------------------------------------------------------------
# C5 — report_content
# ---------------------------------------------------------------------------

class TestC5ReportContent:
    def test_fails_on_empty_report(self):
        empty = make_parsed_report(players=[], raw="")
        r = evaluate(make_parsed_data(), empty, make_run_meta())
        assert get_criterion(r, "report_content")["passed"] is False

    def test_fails_on_short_report(self):
        short = make_parsed_report(raw="short")
        r = evaluate(make_parsed_data(), short, make_run_meta())
        assert get_criterion(r, "report_content")["passed"] is False

    def test_passes_with_content(self):
        r = evaluate(make_parsed_data(), make_parsed_report(), make_run_meta())
        assert get_criterion(r, "report_content")["passed"] is True


# ---------------------------------------------------------------------------
# C6 — historical_context_present
# ---------------------------------------------------------------------------

class TestC6HistoricalContext:
    def test_fails_when_section_absent(self):
        report = make_parsed_report(raw="No history section here. " * 20)
        r = evaluate(make_parsed_data(), report, make_run_meta())
        assert get_criterion(r, "historical_context_present")["passed"] is False

    def test_passes_with_historical_context_header(self):
        report = make_parsed_report(raw="HISTORICAL CONTEXT - blah blah. " * 10)
        r = evaluate(make_parsed_data(), report, make_run_meta())
        assert get_criterion(r, "historical_context_present")["passed"] is True

    def test_passes_with_no_previous_games_phrase(self):
        report = make_parsed_report(raw="No previous games on record for Alice. " * 10)
        r = evaluate(make_parsed_data(), report, make_run_meta())
        assert get_criterion(r, "historical_context_present")["passed"] is True


# ---------------------------------------------------------------------------
# C7 — team_synergy (required when 2+ humans share a team)
# ---------------------------------------------------------------------------

class TestC7TeamSynergy:
    def test_fails_when_section_missing_for_team_game(self):
        report = make_parsed_report(has_team_synergy=False)
        r = evaluate(make_parsed_data(), report, make_run_meta())
        assert get_criterion(r, "team_synergy")["passed"] is False

    def test_passes_when_section_present_for_team_game(self):
        r = evaluate(make_parsed_data(), make_parsed_report(has_team_synergy=True), make_run_meta())
        assert get_criterion(r, "team_synergy")["passed"] is True

    def test_na_for_solo_game(self):
        solo_data = make_parsed_data(players=[
            {"name": "Alice", "civ": "Britons", "civ_id": 0, "is_human": True,
             "team": 1, "winner": True, "eapm": 40},
        ])
        report = make_parsed_report(has_team_synergy=False)
        r = evaluate(solo_data, report, make_run_meta())
        c = get_criterion(r, "team_synergy")
        assert c["passed"] is True
        assert "n/a" in c["note"]

    def test_na_for_players_on_different_teams(self):
        diff_teams = make_parsed_data(players=[
            {"name": "Alice", "civ": "Britons", "civ_id": 0, "is_human": True,
             "team": 1, "winner": True, "eapm": 40},
            {"name": "Bob", "civ": "Franks", "civ_id": 1, "is_human": True,
             "team": 2, "winner": False, "eapm": 35},
        ])
        report = make_parsed_report(has_team_synergy=False)
        r = evaluate(diff_teams, report, make_run_meta())
        c = get_criterion(r, "team_synergy")
        assert c["passed"] is True


# ---------------------------------------------------------------------------
# C8 — solo_no_synergy (team synergy section must be absent for solo games)
# ---------------------------------------------------------------------------

class TestC8SoloNoSynergy:
    def test_fails_when_synergy_section_in_solo_game(self):
        solo_data = make_parsed_data(players=[
            {"name": "Alice", "civ": "Britons", "civ_id": 0, "is_human": True,
             "team": 1, "winner": True, "eapm": 40},
        ])
        report = make_parsed_report(has_team_synergy=True)
        r = evaluate(solo_data, report, make_run_meta())
        assert get_criterion(r, "solo_no_synergy")["passed"] is False

    def test_passes_for_solo_without_synergy(self):
        solo_data = make_parsed_data(players=[
            {"name": "Alice", "civ": "Britons", "civ_id": 0, "is_human": True,
             "team": 1, "winner": True, "eapm": 40},
        ])
        report = make_parsed_report(has_team_synergy=False)
        r = evaluate(solo_data, report, make_run_meta())
        assert get_criterion(r, "solo_no_synergy")["passed"] is True

    def test_na_for_team_game(self):
        r = evaluate(make_parsed_data(), make_parsed_report(), make_run_meta())
        c = get_criterion(r, "solo_no_synergy")
        assert c["passed"] is True
        assert "n/a" in c["note"]


# ---------------------------------------------------------------------------
# C9 — data_limitations_note
# ---------------------------------------------------------------------------

class TestC9DataLimitations:
    def test_fails_when_limited_but_note_absent(self):
        limited = make_parsed_data(limited_data=True)
        report = make_parsed_report(has_data_limitations=False)
        r = evaluate(limited, report, make_run_meta())
        assert get_criterion(r, "data_limitations_note")["passed"] is False

    def test_passes_when_limited_and_note_present(self):
        limited = make_parsed_data(limited_data=True)
        report = make_parsed_report(has_data_limitations=True)
        r = evaluate(limited, report, make_run_meta())
        assert get_criterion(r, "data_limitations_note")["passed"] is True

    def test_na_when_not_limited(self):
        r = evaluate(make_parsed_data(limited_data=False), make_parsed_report(), make_run_meta())
        c = get_criterion(r, "data_limitations_note")
        assert c["passed"] is True
        assert "n/a" in c["note"]


# ---------------------------------------------------------------------------
# C10 — report_written
# ---------------------------------------------------------------------------

class TestC10ReportWritten:
    def test_fails_when_file_missing(self):
        r = evaluate(make_parsed_data(), make_parsed_report(), make_run_meta(report_path_exists=False))
        assert get_criterion(r, "report_written")["passed"] is False

    def test_passes_when_file_exists(self):
        r = evaluate(make_parsed_data(), make_parsed_report(), make_run_meta(report_path_exists=True))
        assert get_criterion(r, "report_written")["passed"] is True


# ---------------------------------------------------------------------------
# C11 — run_entry_and_chroma
# ---------------------------------------------------------------------------

class TestC11RunEntryAndChroma:
    def test_fails_when_run_entry_missing(self):
        r = evaluate(make_parsed_data(), make_parsed_report(),
                     make_run_meta(run_entry_written=False))
        assert get_criterion(r, "run_entry_and_chroma")["passed"] is False

    def test_fails_when_chroma_not_stored(self):
        r = evaluate(make_parsed_data(), make_parsed_report(),
                     make_run_meta(chroma_stored=False))
        assert get_criterion(r, "run_entry_and_chroma")["passed"] is False

    def test_passes_when_both_written(self):
        r = evaluate(make_parsed_data(), make_parsed_report(), make_run_meta())
        assert get_criterion(r, "run_entry_and_chroma")["passed"] is True


# ---------------------------------------------------------------------------
# Score and threshold
# ---------------------------------------------------------------------------

class TestScoringAndThreshold:
    def test_score_formula(self):
        # Force exactly 8 criteria to pass (c10 fail + c11 fail + c3 fail = 3 failures)
        run_meta = make_run_meta(report_path_exists=False, run_entry_written=False, chroma_stored=False)
        report = make_parsed_report(players=[
            {"name": "dreas.kesbeke", "civ": "Byzantines", "eapm": 16, "result": "Win"},
            # walter2515 missing -> c3 fails
        ])
        r = evaluate(make_parsed_data(), report, run_meta)
        assert r["score"] == round(8 / 11, 3)

    def test_8_of_11_passes(self):
        run_meta = make_run_meta(report_path_exists=False, run_entry_written=False, chroma_stored=False)
        report = make_parsed_report(players=[
            {"name": "dreas.kesbeke", "civ": "Byzantines", "eapm": 16, "result": "Win"},
        ])
        r = evaluate(make_parsed_data(), report, run_meta)
        assert r["passed"] is True  # 8/11 >= 0.7

    def test_7_of_11_fails(self):
        # 4 failures: c10, c11, c3, c6
        run_meta = make_run_meta(report_path_exists=False, run_entry_written=False, chroma_stored=False)
        report = make_parsed_report(
            players=[{"name": "dreas.kesbeke", "civ": "Byzantines", "eapm": 16, "result": "Win"}],
            # Raw has no "historical context" or "no previous games on record" phrase -> c6 fails
            raw="Player performed well in this match. Excellent micro observed. " * 10,
        )
        r = evaluate(make_parsed_data(), report, run_meta)
        assert r["passed"] is False
