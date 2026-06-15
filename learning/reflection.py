"""
Reflection: analyses the full run history to identify patterns across players,
civs, and evaluator criteria. Writes conclusions to ChromaDB so the main agent
can retrieve them as context on future runs. Also writes a human-readable
markdown report to logs/.

Trigger manually: python reflect.py
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

import anthropic

from config import ANTHROPIC_API_KEY, CLAUDE_MODEL, LOGS_PATH, RUNS_PATH
from core.database import upsert

REFLECTION_SYSTEM_PROMPT = """\
You are analysing the run history of an Age of Empires II coaching agent.
Your job is to identify patterns across runs that will make future coaching reports more useful.

Focus on:
1. Player performance trends: eAPM levels, civilisation choices, win rates
2. Which evaluator criteria failed most often and why
3. Team patterns: recurring player combinations, synergy signals
4. Coaching quality trend: are scores improving over time?

Write your conclusions as a numbered list. Each point must be:
- Specific and grounded in the data — no generic observations
- Directly actionable for a future coaching report
- Concise (one or two sentences)

Do not summarise the raw data or pad the response. Only write insights.\
"""


def load_run_history() -> list[dict]:
    """
    Read all JSONL files from data/runs/. Deduplicate by run_id, preferring
    the entry that has a non-null evaluator_score (the post-evaluation write).
    """
    if not RUNS_PATH.exists():
        return []

    by_id: dict[str, dict] = {}
    for jsonl_file in sorted(RUNS_PATH.glob("*.jsonl")):
        for line in jsonl_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            run_id = entry.get("run_id")
            if not run_id:
                continue
            existing = by_id.get(run_id)
            # Keep whichever entry has an evaluator score; if both do, keep the
            # later one (longer timestamp string sorts higher lexicographically).
            if existing is None:
                by_id[run_id] = entry
            elif (entry.get("evaluator_score") is not None
                  and existing.get("evaluator_score") is None):
                by_id[run_id] = entry
            elif (entry.get("evaluator_score") is not None
                  and existing.get("evaluator_score") is not None
                  and entry.get("timestamp", "") > existing.get("timestamp", "")):
                by_id[run_id] = entry

    return list(by_id.values())


def _format_entries(entries: list[dict]) -> str:
    """Format run entries as readable lines for the reflection prompt."""
    lines = []
    for e in entries:
        run_id = e.get("run_id", "?")[:8]
        ts = e.get("timestamp", "?")[:10]
        score = e.get("evaluator_score")
        score_str = f"{score:.3f}" if score is not None else "n/a"
        passed = "PASS" if e.get("evaluator_passed") else ("FAIL" if score is not None else "n/a")
        players = e.get("players", [])
        player_str = ", ".join(
            f"{p.get('name', '?')} "
            f"({p.get('civ', '?')} "
            f"eAPM={p.get('eapm', p.get('eAPM', '?'))})"
            for p in players
        )
        failing = [c["name"] for c in e.get("criteria", []) if not c.get("passed")]
        failing_str = ", ".join(failing) if failing else "none"
        lines.append(
            f"Run {run_id} | {ts} | score={score_str} {passed} | "
            f"players: {player_str} | failing criteria: {failing_str}"
        )
    return "\n".join(lines)


def reflect(min_runs: int = 3) -> dict:
    """
    Load run history, call Claude to identify patterns, store conclusions in
    ChromaDB, and write a markdown report to logs/.

    Returns:
        {
            "conclusions": str,
            "runs_analyzed": int,
            "report_path": str | None,
            "skipped": bool,
        }
    """
    entries = load_run_history()
    # Only analyse runs that completed evaluation — earlier partial entries lack scores.
    scored = [e for e in entries if e.get("evaluator_score") is not None]

    print(f"[reflect] {len(scored)} scored runs found (min required: {min_runs})")

    if len(scored) < min_runs:
        print(f"[reflect] Not enough scored runs yet — skipping.")
        return {"conclusions": "", "runs_analyzed": len(scored), "report_path": None, "skipped": True}

    history_text = _format_entries(scored)
    user_message = (
        f"Here is the run history ({len(scored)} runs):\n\n"
        f"{history_text}\n\n"
        "Identify patterns and write your conclusions as a numbered list."
    )

    print(f"[reflect] Calling Claude to analyse {len(scored)} runs ...")
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=2000,
        system=REFLECTION_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )
    conclusions = response.content[0].text.strip()
    print(f"[reflect] Conclusions received ({len(conclusions)} chars)")

    # Store in ChromaDB so the main agent can retrieve it as context on future runs.
    reflection_id = (
        f"reflection-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{str(uuid.uuid4())[:8]}"
    )
    upsert(
        "reflections",
        ids=[reflection_id],
        documents=[conclusions],
        metadatas=[{
            "type": "reflection",
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "runs_analyzed": str(len(scored)),
        }],
    )
    print(f"[reflect] Stored in ChromaDB: {reflection_id}")

    report_path = _write_report(conclusions, scored, reflection_id)
    print(f"[reflect] Report: {report_path}")

    return {
        "conclusions": conclusions,
        "runs_analyzed": len(scored),
        "report_path": str(report_path),
        "skipped": False,
    }


def _write_report(conclusions: str, entries: list[dict], reflection_id: str) -> Path:
    LOGS_PATH.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    path = LOGS_PATH / f"reflection_{date_str}.md"

    players_seen: set[str] = set()
    for e in entries:
        for p in e.get("players", []):
            name = p.get("name")
            if name:
                players_seen.add(name)

    content = (
        f"# Reflection — {date_str}\n\n"
        f"**ID:** {reflection_id}  \n"
        f"**Runs analysed:** {len(entries)}  \n"
        f"**Players seen:** {', '.join(sorted(players_seen))}  \n\n"
        f"## Conclusions\n\n"
        f"{conclusions}\n"
    )
    path.write_text(content, encoding="utf-8")
    return path
