"""
RAG queries against ChromaDB. Returns relevant past context for use in the
agent's prompt — player history, team history, and civ knowledge.
"""

from core.database import get_all, query

COLLECTION_RUNS = "runs"
COLLECTION_CIV = "civ_knowledge"
COLLECTION_REFLECTIONS = "reflections"


def get_player_history(player_names: list[str], n_results: int = 5) -> list[dict]:
    """
    Retrieve past run summaries for one or more players in a single query.
    Returns a flat list of results across all named players.
    """
    if not player_names:
        return []
    results = query(COLLECTION_RUNS, query_texts=player_names, n_results=n_results)
    return _flatten(results)


def get_team_history(player_names: list[str], n_results: int = 5) -> list[dict]:
    """
    Retrieve past games where all named players appeared on the same team.
    Exact combination match only — no partial matches.
    """
    if len(player_names) < 2:
        return []
    query_text = " ".join(sorted(player_names))
    results = query(COLLECTION_RUNS, query_texts=[query_text], n_results=n_results * 3)
    all_results = _flatten(results)
    # Filter to entries that contain every player in the combination
    lower_names = [n.lower() for n in player_names]
    return [
        r for r in all_results
        if all(n in r.get("document", "").lower() for n in lower_names)
    ][:n_results]


def get_civ_knowledge(civ_name: str) -> list[dict]:
    """
    Retrieve ingested domain knowledge about a specific civilisation.
    """
    if not civ_name:
        return []
    results = query(COLLECTION_CIV, query_texts=[civ_name], n_results=3)
    return _flatten(results)


def get_reflections(n: int = 3) -> list[dict]:
    """
    Return the n most recent reflection conclusions from ChromaDB, sorted by date.
    Returns an empty list if no reflections have been stored yet.
    """
    result = get_all(COLLECTION_REFLECTIONS)
    flat = []
    ids = result.get("ids", [])
    docs = result.get("documents", [])
    metas = result.get("metadatas", [])
    for i, doc_id in enumerate(ids):
        flat.append({
            "id": doc_id,
            "document": docs[i] if i < len(docs) else "",
            "metadata": metas[i] if i < len(metas) else {},
        })
    flat.sort(key=lambda r: r["metadata"].get("date", ""), reverse=True)
    return flat[:n]


def _flatten(results: dict) -> list[dict]:
    flat = []
    ids = results.get("ids", [[]])[0]
    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    for i, doc_id in enumerate(ids):
        flat.append({
            "id": doc_id,
            "document": docs[i] if i < len(docs) else "",
            "metadata": metas[i] if i < len(metas) else {},
        })
    return flat
