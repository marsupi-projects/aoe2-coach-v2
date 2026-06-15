"""
Prompts sent to the Claude model. System prompt defines the agent's role;
task prompt is assembled at runtime from the replay file path and run context.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from config import PROMPTS_PATH

PROMPT_VERSION = "v1.0"

SYSTEM_PROMPT = """\
You are an Age of Empires II coaching agent. Your job is to analyse a replay \
file and produce a structured coaching report for every human player in the game.

Rules you must follow without exception:
- Never fabricate stats that are not present in the parsed replay data. If a \
field is null or unavailable, say so explicitly — never estimate or infer.
- Every human player must have an individual section covering civ, eAPM, \
win/loss, historical context, observations, and recommendations.
- Historical context is mandatory for every human player. If no past games \
exist, write "No previous games on record for [player]".
- When two or more human players share a team, include a Team Synergy section. \
If no shared history exists, write "No shared games on record for this combination".
- When only one human player is present, omit the Team Synergy section entirely.
- AI players (user_id == 0xFFFFFFFF) must never appear in the coaching output.
- If feudal time, castle time, or resource stats are unavailable (custom lobby \
or vs-AI game), include a Data Limitations section and do not reference those stats.

Workflow:
1. Call parse_replay with the provided file path.
2. Call get_player_history with all human player names in one call.
3. If two or more human players share a team, call get_team_history.
4. For each human player's civilisation, call get_civ_knowledge.
5. Produce the full coaching report text.
6. Call write_coaching_report with the report text and run_id.
7. Call write_run_entry with the completed run record.
8. Call store_run_memory with a plain-text summary of this run.
"""


def build_task_prompt(
    file_path: str,
    run_id: str,
    reflections: list[dict] | None = None,
) -> str:
    lines = [
        f"Run ID: {run_id}",
        f"Replay file: {file_path}",
        f"Date: {datetime.utcnow().strftime('%Y-%m-%d')}",
    ]
    if reflections:
        lines.append(
            "\nRECENT REFLECTIONS\n"
            "The following patterns were identified across previous runs. "
            "Use these to make your coaching report more specific and informed:"
        )
        for r in reflections:
            date = r.get("metadata", {}).get("date", "")
            lines.append(f"\n[{date}]\n{r['document']}")
    lines.append(
        "\nParse this replay and produce a coaching report following the rules "
        "in the system prompt. Use the tools available to you in sequence."
    )
    return "\n".join(lines)


def save_prompt_snapshot(system: str, task: str, run_id: str) -> None:
    PROMPTS_PATH.mkdir(parents=True, exist_ok=True)
    snapshot = {
        "version": PROMPT_VERSION,
        "run_id": run_id,
        "timestamp": datetime.utcnow().isoformat(),
        "system": system,
        "task": task,
    }
    path = PROMPTS_PATH / f"{run_id}_prompt.json"
    path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
