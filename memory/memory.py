"""
Assembles the context window for each Claude model call.
Reads retrieved history and formats it for injection into the task prompt.
Kept simple in v1.1 — no truncation logic needed yet at this scale.
"""

from __future__ import annotations

from memory.retrieval import get_player_history, get_team_history, get_civ_knowledge


def build_context(player_names: list[str], civ_names: list[str]) -> str:
    """
    Fetch relevant past context for the given players and civs, and return
    a formatted string ready to prepend to the task prompt.
    """
    sections: list[str] = []

    history = get_player_history(player_names)
    if history:
        lines = ["--- RETRIEVED PLAYER HISTORY ---"]
        for entry in history:
            lines.append(entry["document"])
        sections.append("\n".join(lines))

    civ_knowledge: list[str] = []
    for civ in civ_names:
        results = get_civ_knowledge(civ)
        for r in results:
            civ_knowledge.append(r["document"])
    if civ_knowledge:
        lines = ["--- RETRIEVED CIV KNOWLEDGE ---"] + civ_knowledge
        sections.append("\n".join(lines))

    return "\n\n".join(sections)
