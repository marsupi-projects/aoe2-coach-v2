"""
Extracts structured output from the Claude model's final text response.
The agent's final message is expected to be the coaching report in plain text;
parser.py pulls out the fields the rest of the system needs to act on.
"""

from __future__ import annotations

import re


def extract_report(response_text: str) -> dict:
    """
    Parse the coaching report text into a structured dict.
    Returns:
        {
            "raw": str,              # full report as-is
            "players": list[dict],   # one dict per player block found
            "has_team_synergy": bool,
            "has_data_limitations": bool,
        }
    """
    raw = response_text.strip()
    return {
        "raw": raw,
        "players": _extract_players(raw),
        "has_team_synergy": bool(re.search(r"TEAM SYNERGY", raw, re.IGNORECASE)),
        "has_data_limitations": bool(re.search(r"DATA LIMITATIONS", raw, re.IGNORECASE)),
    }


def _extract_players(text: str) -> list[dict]:
    """
    Find each PLAYER block and pull name, civ, eAPM, and result.

    Handles two formats:
      Format 1 (single-line): PLAYER: Name | Civ | eAPM: N | Result: Win/Loss
      Format 2 (multi-line):  PLAYER N — Name
                                Civilisation : Civ
                                eAPM         : N
                                Result       : ✅ Win
    Tries format 1 first; falls back to format 2 if nothing is found.
    """
    # Format 1
    inline = re.compile(
        r"PLAYER:\s*(?P<name>[^|\n]+)\|\s*(?P<civ>[^|\n]+)\|\s*eAPM:\s*(?P<eapm>\d+)\s*\|\s*Result:\s*(?P<result>\w+)",
        re.IGNORECASE,
    )
    players = [
        {
            "name": m.group("name").strip(),
            "civ": m.group("civ").strip(),
            "eapm": int(m.group("eapm")),
            "result": m.group("result").strip(),
        }
        for m in inline.finditer(text)
    ]
    if players:
        return players

    # Format 2: "  PLAYER 1 — Name" or "PLAYER: Name" on its own line
    header_re = re.compile(
        r"^\s*PLAYER(?:\s+\d+)?\s*[:—–\-]\s*(?P<name>[^\n\r]+)",
        re.IGNORECASE | re.MULTILINE,
    )
    headers = list(header_re.finditer(text))
    for i, hm in enumerate(headers):
        name = hm.group("name").strip()
        # Slice this player's block up to the next PLAYER header (or end of text)
        start = hm.end()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(text)
        block = text[start:end]

        civ_m = re.search(r"Civili[sz]ation\s*:\s*(.+)", block, re.IGNORECASE)
        eapm_m = re.search(r"eAPM\s*:\s*(\d+)", block, re.IGNORECASE)
        result_m = re.search(r"Result\s*:\s*(.+)", block, re.IGNORECASE)

        if not (civ_m and eapm_m):
            continue

        # Strip emojis/symbols: "✅ Win" → "Win", "❌ Loss" → "Loss"
        result_raw = result_m.group(1).strip() if result_m else ""
        result_clean = re.sub(r"[^\w\s]", "", result_raw).strip()
        result_word = result_clean.split()[0] if result_clean else ""

        players.append({
            "name": name,
            "civ": civ_m.group(1).strip(),
            "eapm": int(eapm_m.group(1)),
            "result": result_word,
        })

    return players
