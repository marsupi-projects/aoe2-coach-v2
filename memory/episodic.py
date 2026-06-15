"""
Stores the agent's own run memories in ChromaDB so future runs can retrieve
what the agent did and observed in past games.
"""

from core.database import upsert
from memory.retrieval import COLLECTION_RUNS


def store_run_memory(run_id: str, summary: str, metadata: dict) -> None:
    """
    Embed and store a run summary in ChromaDB.
    summary  — plain-text description of the run (players, civs, result, score)
    metadata — structured fields for filtering (player names, date, run_id)
    """
    upsert(
        collection_name=COLLECTION_RUNS,
        ids=[run_id],
        documents=[summary],
        metadatas=[metadata],
    )
