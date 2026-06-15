"""
Rule-based evaluator. Scores a completed run against the 11 success criteria
in SPEC.md §3. Score = criteria_met / 11. Pass threshold: >= 0.7 (8/11).

Each criterion returns (passed: bool, note: str). Notes surface in feedback.py
so patterns of failure are visible across runs.
"""

from __future__ import annotations

import re
from config import EVALUATOR_PASS_THRESHOLD, EVALUATOR_CRITERIA_COUNT


def evaluate(parsed_data: dict, parsed_report: dict, run_meta: dict) -> dict:
    """
    parsed_data   — output of parse_replay (player list, duration, etc.)
    parsed_report — output of parser.extract_report
    run_meta      — dict with keys: report_path_exists, run_entry_written,
                    chroma_stored, elapsed_seconds

    Returns:
        {
            "score": float,       # 0.0 – 1.0
            "passed": bool,
            "criteria": list[dict],  # one per criterion
        }
    """
    criteria = [
        _c1_replay_parsed(parsed_data),
        _c2_human_players_identified(parsed_data),
        _c3_all_players_covered(parsed_data, parsed_report),
        _c4_civ_names_resolved(parsed_report),
        _c5_report_content(parsed_report),
        _c6_historical_context(parsed_data, parsed_report),
        _c7_team_synergy(parsed_data, parsed_report),
        _c8_solo_no_synergy(parsed_data, parsed_report),
        _c9_data_limitations(parsed_data, parsed_report),
        _c10_report_written(run_meta),
        _c11_run_entry_and_chroma(run_meta),
    ]

    met = sum(1 for c in criteria if c["passed"])
    score = met / EVALUATOR_CRITERIA_COUNT

    return {
        "score": round(score, 3),
        "passed": score >= EVALUATOR_PASS_THRESHOLD,
        "criteria": criteria,
    }


def _c(name: str, passed: bool, note: str = "") -> dict:
    return {"name": name, "passed": passed, "note": note}


def _human_players(parsed_data: dict) -> list[dict]:
    return [p for p in parsed_data.get("players", []) if p.get("is_human", True)]


def _c1_replay_parsed(parsed_data: dict) -> dict:
    ok = bool(parsed_data) and "players" in parsed_data
    return _c("replay_parsed", ok, "" if ok else "parsed_data is empty or missing players key")


def _c2_human_players_identified(parsed_data: dict) -> dict:
    humans = _human_players(parsed_data)
    ok = len(humans) >= 1
    return _c("human_players_identified", ok, "" if ok else "no human players found")


def _c3_all_players_covered(parsed_data: dict, parsed_report: dict) -> dict:
    humans = _human_players(parsed_data)
    report_names = {p["name"].lower() for p in parsed_report.get("players", [])}
    missing = [p["name"] for p in humans if p["name"].lower() not in report_names]
    ok = len(missing) == 0
    return _c("all_players_covered", ok, "" if ok else f"missing: {missing}")


def _c4_civ_names_resolved(parsed_report: dict) -> dict:
    raw = parsed_report.get("raw", "")
    bad = re.findall(r"\bciv_\d+\b", raw, re.IGNORECASE)
    ok = len(bad) == 0
    return _c("civ_names_resolved", ok, "" if ok else f"raw civ IDs found: {bad}")


def _c5_report_content(parsed_report: dict) -> dict:
    players = parsed_report.get("players", [])
    ok = len(players) >= 1 and len(parsed_report.get("raw", "")) > 200
    return _c("report_content", ok, "" if ok else "report appears empty or too short")


def _c6_historical_context(parsed_data: dict, parsed_report: dict) -> dict:
    raw = parsed_report.get("raw", "").lower()
    ok = "historical context" in raw or "no previous games on record" in raw
    return _c("historical_context_present", ok, "" if ok else "historical context section not found")


def _c7_team_synergy(parsed_data: dict, parsed_report: dict) -> dict:
    humans = _human_players(parsed_data)
    teams: dict[int, list] = {}
    for p in humans:
        teams.setdefault(p.get("team", 0), []).append(p)
    multi_team = any(len(members) >= 2 for members in teams.values())
    if not multi_team:
        return _c("team_synergy", True, "n/a — no team with 2+ human players")
    ok = parsed_report.get("has_team_synergy", False)
    return _c("team_synergy", ok, "" if ok else "team synergy section missing")


def _c8_solo_no_synergy(parsed_data: dict, parsed_report: dict) -> dict:
    humans = _human_players(parsed_data)
    if len(humans) != 1:
        return _c("solo_no_synergy", True, "n/a — not a solo game")
    ok = not parsed_report.get("has_team_synergy", False)
    return _c("solo_no_synergy", ok, "" if ok else "team synergy section present in solo game")


def _c9_data_limitations(parsed_data: dict, parsed_report: dict) -> dict:
    is_limited = parsed_data.get("limited_data", False)
    if not is_limited:
        return _c("data_limitations_note", True, "n/a — full data available")
    ok = parsed_report.get("has_data_limitations", False)
    return _c("data_limitations_note", ok, "" if ok else "data limitations section missing for limited game")


def _c10_report_written(run_meta: dict) -> dict:
    ok = run_meta.get("report_path_exists", False)
    return _c("report_written", ok, "" if ok else "coaching report file not found")


def _c11_run_entry_and_chroma(run_meta: dict) -> dict:
    ok = run_meta.get("run_entry_written", False) and run_meta.get("chroma_stored", False)
    return _c("run_entry_and_chroma", ok, "" if ok else "run entry or chroma write missing")
