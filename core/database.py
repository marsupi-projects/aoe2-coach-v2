"""
Single interface to ChromaDB. All modules that need vector database access go
through here — no other module opens a ChromaDB client directly.

Client selection:
  CHROMA_HOST set   → HttpClient (Docker: ChromaDB runs as a separate container)
  CHROMA_HOST unset → PersistentClient (local dev: reads files directly from disk)
"""

from __future__ import annotations

import chromadb
from chromadb import Collection
from config import CHROMA_HOST, CHROMA_PATH

_client: chromadb.ClientAPI | None = None


def _get_client() -> chromadb.ClientAPI:
    global _client
    if _client is None:
        if CHROMA_HOST:
            # Docker mode: ChromaDB is a separate container reachable over HTTP
            _client = chromadb.HttpClient(host=CHROMA_HOST, port=8000)
        else:
            _client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    return _client


def get_collection(name: str) -> Collection:
    return _get_client().get_or_create_collection(name)


def upsert(collection_name: str, ids: list[str], documents: list[str], metadatas: list[dict]) -> None:
    col = get_collection(collection_name)
    col.upsert(ids=ids, documents=documents, metadatas=metadatas)


def query(collection_name: str, query_texts: list[str], n_results: int = 5) -> dict:
    col = get_collection(collection_name)
    count = col.count()
    if count == 0:
        return {"ids": [[]], "documents": [[]], "metadatas": [[]]}
    return col.query(query_texts=query_texts, n_results=min(n_results, count))


def get_all(collection_name: str, limit: int = 50) -> dict:
    """Non-semantic retrieval: returns all documents in a collection up to limit.
    Returns flat lists (not nested), unlike query() which returns nested lists."""
    col = get_collection(collection_name)
    if col.count() == 0:
        return {"ids": [], "documents": [], "metadatas": []}
    return col.get(limit=limit, include=["documents", "metadatas"])
