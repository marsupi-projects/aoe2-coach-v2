"""
Tool definitions and implementations for the aoe2-coach agent.

The Claude model requests tools by name; agent.py dispatches to the functions
here. No raw SQL or direct ChromaDB access — all persistence goes through
database.py, retrieval.py, and episodic.py.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path

from config import REPORTS_PATH, RUNS_PATH, AI_PLAYER_SENTINEL

# Populated by parse_replay so tool_write_coaching_report can build the filename
# without needing extra parameters from Claude. Safe for single-threaded local use.
_last_parsed: dict = {}
from memory.retrieval import get_player_history, get_team_history, get_civ_knowledge
from memory.episodic import store_run_memory

# ---------------------------------------------------------------------------
# Tool definitions (sent to the Claude API as the `tools` parameter)
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS = [
    {
        "name": "parse_replay",
        "description": (
            "Parse a .aoe2record replay file and return structured data: "
            "players (name, civ, eAPM, is_human, team, winner), game duration, "
            "map name, game type, and a note describing any data limitations."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Path to the .aoe2record file"}
            },
            "required": ["file_path"],
        },
    },
    {
        "name": "get_player_history",
        "description": (
            "Retrieve past run summaries from ChromaDB for one or more players. "
            "Returns a list of past games (date, civ, eAPM, result, duration) "
            "per player. Returns an empty list if no past games exist."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "player_names": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of human player names to look up",
                }
            },
            "required": ["player_names"],
        },
    },
    {
        "name": "get_team_history",
        "description": (
            "Retrieve past games where all named players appeared on the same team. "
            "Exact combination only — no partial matches. Returns an empty list if "
            "no shared games exist."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "player_names": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of human player names who must all appear together",
                }
            },
            "required": ["player_names"],
        },
    },
    {
        "name": "get_civ_knowledge",
        "description": (
            "Retrieve ingested domain knowledge about a specific civilisation: "
            "unit strengths, typical build orders, common weaknesses."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "civ_name": {"type": "string", "description": "Civilisation name, e.g. 'Britons'"}
            },
            "required": ["civ_name"],
        },
    },
    {
        "name": "write_run_entry",
        "description": "Append the completed run record to data/runs/ as a JSONL entry.",
        "input_schema": {
            "type": "object",
            "properties": {
                "run_data": {
                    "type": "object",
                    "description": "Run record containing run_id, timestamp, replay_file, players, coaching_report_path, evaluator_score, prompt_version",
                }
            },
            "required": ["run_data"],
        },
    },
    {
        "name": "write_coaching_report",
        "description": "Write the coaching report as a .txt file to data/reports/.",
        "input_schema": {
            "type": "object",
            "properties": {
                "report_text": {"type": "string", "description": "Full coaching report text"},
                "run_id": {"type": "string", "description": "Run ID used to name the file"},
            },
            "required": ["report_text", "run_id"],
        },
    },
    {
        "name": "store_run_memory",
        "description": "Embed and store the run summary in ChromaDB via episodic memory.",
        "input_schema": {
            "type": "object",
            "properties": {
                "summary": {"type": "string", "description": "Plain-text summary of the run for semantic retrieval"},
                "metadata": {"type": "object", "description": "Structured fields: players, date, run_id"},
            },
            "required": ["summary", "metadata"],
        },
    },
]

# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def parse_replay(file_path: str) -> dict:
    """
    Parse a .aoe2record file using mgz.model.parse_match (Kjir fork, commit b4a30d8).
    AI players are detected by profile_id == AI_PLAYER_SENTINEL (0xFFFFFFFF).
    Civ names are strings from mgz (e.g. 'Britons'), not raw IDs.

    Migration note: when happyleavesaoc/aoc-mgz releases a fix for patch
    v101.103.47452.0+, replace the fork pin in requirements.txt and verify
    this function still passes a round-trip parse on a current-patch replay.
    """
    from mgz.model import parse_match  # local import keeps startup fast

    with open(file_path, "rb") as f:
        match = parse_match(f)

    # Build team lookup: player object -> 1-based team index
    team_map: dict[int, int] = {}  # player number -> team index
    for team_idx, team_members in enumerate(match.teams, start=1):
        for p in team_members:
            team_map[p.number] = team_idx

    players = []
    for p in match.players:
        is_human = p.profile_id != AI_PLAYER_SENTINEL
        players.append({
            "name": p.name,
            "civ": p.civilization,          # string, e.g. 'Britons'
            "civ_id": p.civilization_id,
            "is_human": is_human,
            "team": team_map.get(p.number),
            "winner": p.winner,
            "eapm": p.eapm,
            "profile_id": p.profile_id,
        })

    has_ai = any(not p["is_human"] for p in players)
    duration_secs = match.duration.total_seconds() if match.duration else None

    note = (
        "vs-AI or custom lobby game. Feudal time, castle time, and resource "
        "stats are not available in the replay data."
        if has_ai else
        "Multiplayer game. Achievement stats may not be present in this replay."
    )

    result = {
        "players": players,
        "duration_seconds": duration_secs,
        "duration_str": str(match.duration) if match.duration else None,
        "map_name": match.map.name if match.map else None,
        "game_type": match.type,
        "completed": match.completed,
        "limited_data": has_ai,  # True for vs-AI/custom lobby; triggers c9 check
        "note": note,
        "game_date": match.timestamp.strftime("%Y%m%d") if match.timestamp else None,
    }
    global _last_parsed
    _last_parsed = result
    return result


def tool_get_player_history(player_names: list[str]) -> list[dict]:
    return get_player_history(player_names)


def tool_get_team_history(player_names: list[str]) -> list[dict]:
    return get_team_history(player_names)


def tool_get_civ_knowledge(civ_name: str) -> list[dict]:
    return get_civ_knowledge(civ_name)


def tool_write_run_entry(run_data: dict) -> str:
    RUNS_PATH.mkdir(parents=True, exist_ok=True)
    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    path = RUNS_PATH / f"{date_str}.jsonl"
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(run_data) + "\n")
    return str(path)


def build_report_filename(parsed_data: dict, analysis_date: str) -> str:
    """
    Construct a human-readable report filename from replay metadata.
    Format: {game_date}_{civs}_{map}_{result}_{analysis_date}.txt
    Example: 20260613_byzantines-aztecs_wade_win_20260615.txt
    Multiple civs are joined with '-'; spaces in map names become '_'.
    Falls back to analysis_date for game_date when the replay has no timestamp.
    """
    humans = [p for p in parsed_data.get("players", []) if p.get("is_human")]
    civs = "-".join(p["civ"].lower().replace(" ", "_") for p in humans) or "unknown"
    map_name = (parsed_data.get("map_name") or "unknown").lower().replace(" ", "_")
    result = "win" if any(p.get("winner") for p in humans) else "loss"
    game_date = parsed_data.get("game_date") or analysis_date
    return f"{game_date}_{civs}_{map_name}_{result}_{analysis_date}.txt"


def tool_write_coaching_report(report_text: str, run_id: str) -> str:
    analysis_date = datetime.utcnow().strftime("%Y%m%d")
    filename = build_report_filename(_last_parsed, analysis_date) if _last_parsed else f"{run_id}.txt"
    REPORTS_PATH.mkdir(parents=True, exist_ok=True)
    path = REPORTS_PATH / filename
    path.write_text(report_text, encoding="utf-8")
    return str(path)


def tool_store_run_memory(summary: str, metadata: dict) -> str:
    run_id = metadata.get("run_id", str(uuid.uuid4()))
    store_run_memory(run_id=run_id, summary=summary, metadata=metadata)
    return f"stored memory for run {run_id}"


# ---------------------------------------------------------------------------
# Dispatcher — agent.py calls this with the tool name and raw input dict
# ---------------------------------------------------------------------------

TOOL_HANDLERS: dict[str, callable] = {
    "parse_replay": lambda inp: parse_replay(inp["file_path"]),
    "get_player_history": lambda inp: tool_get_player_history(inp["player_names"]),
    "get_team_history": lambda inp: tool_get_team_history(inp["player_names"]),
    "get_civ_knowledge": lambda inp: tool_get_civ_knowledge(inp["civ_name"]),
    "write_run_entry": lambda inp: tool_write_run_entry(inp["run_data"]),
    "write_coaching_report": lambda inp: tool_write_coaching_report(inp["report_text"], inp["run_id"]),
    "store_run_memory": lambda inp: tool_store_run_memory(inp["summary"], inp["metadata"]),
}


def dispatch(tool_name: str, tool_input: dict):
    handler = TOOL_HANDLERS.get(tool_name)
    if handler is None:
        raise ValueError(f"Unknown tool: {tool_name}")
    return handler(tool_input)
