"""
Ingests external domain knowledge into ChromaDB so the agent can retrieve it
via get_civ_knowledge() during coaching runs.

Currently handles civ knowledge files from data/knowledge/civs/*.json.
Each file is converted to a plain-text document and upserted into the
'civ_knowledge' collection. Re-running is safe — upsert overwrites by ID.

Run manually: python -m memory.ingestion
"""

from __future__ import annotations

import json
from pathlib import Path

from config import KNOWLEDGE_PATH
from core.database import upsert
from memory.retrieval import COLLECTION_CIV

CIV_DIR = KNOWLEDGE_PATH / "civs"


def _civ_to_document(data: dict) -> str:
    """Convert a civ JSON dict into a prose document suitable for embedding."""
    lines = [f"Civilisation: {data['civ']}", ""]

    if data.get("strengths"):
        lines.append("Strengths: " + "; ".join(data["strengths"]))

    if data.get("weaknesses"):
        lines.append("Weaknesses: " + "; ".join(data["weaknesses"]))

    if data.get("unique_unit"):
        lines.append(f"Unique Unit: {data['unique_unit']}")

    tech = data.get("unique_tech", {})
    if isinstance(tech, dict):
        lines.append("Unique Technologies:")
        if tech.get("castle_age"):
            lines.append(f"  Castle Age: {tech['castle_age']}")
        if tech.get("imperial_age"):
            lines.append(f"  Imperial Age: {tech['imperial_age']}")
    elif isinstance(tech, str) and tech:
        lines.append(f"Unique Technology: {tech}")

    if data.get("economy_bonuses"):
        lines.append("Economy Bonuses: " + "; ".join(data["economy_bonuses"]))

    if data.get("team_bonus"):
        lines.append(f"Team Bonus: {data['team_bonus']}")

    if data.get("build_order_notes"):
        lines.append(f"Build Order Notes: {data['build_order_notes']}")

    if data.get("common_pairings"):
        lines.append("Common Pairings: " + "; ".join(data["common_pairings"]))

    spikes = data.get("power_spikes", {})
    if isinstance(spikes, dict) and any(spikes.values()):
        lines.append("Power Spikes:")
        for age in ("feudal_age", "castle_age", "imperial_age"):
            if spikes.get(age):
                label = age.replace("_", " ").title()
                lines.append(f"  {label}: {spikes[age]}")

    return "\n".join(lines)


def ingest_civs() -> int:
    """
    Read all civ JSON files from data/knowledge/civs/, skip _template.json,
    and upsert each into ChromaDB. Returns the number of civs ingested.
    """
    if not CIV_DIR.exists():
        print(f"[ingestion] {CIV_DIR} does not exist — nothing to ingest.")
        return 0

    files = [f for f in sorted(CIV_DIR.glob("*.json")) if f.stem != "_template"]
    if not files:
        print("[ingestion] No civ files found.")
        return 0

    ids, documents, metadatas = [], [], []

    for path in files:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"[ingestion] Skipping {path.name} — invalid JSON: {e}")
            continue

        civ_name = data.get("civ", path.stem).strip()
        if not civ_name:
            print(f"[ingestion] Skipping {path.name} — missing civ name.")
            continue

        doc_id = f"civ_{civ_name.lower().replace(' ', '_')}"
        ids.append(doc_id)
        documents.append(_civ_to_document(data))
        metadatas.append({"type": "civ_knowledge", "civ": civ_name})
        print(f"[ingestion] Prepared: {civ_name} ({doc_id})")

    if ids:
        upsert(COLLECTION_CIV, ids=ids, documents=documents, metadatas=metadatas)
        print(f"[ingestion] Upserted {len(ids)} civ(s) into '{COLLECTION_CIV}'.")

    return len(ids)


if __name__ == "__main__":
    ingested = ingest_civs()
    print(f"[ingestion] Done — {ingested} civ(s) ingested.")
