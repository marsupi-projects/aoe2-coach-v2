"""
Thin wrapper around ChromaDB's default embedding function.
Keeping this isolated means swapping the embedding model later
only requires changing this file.
"""

from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

_ef = DefaultEmbeddingFunction()


def embed(texts: list[str]) -> list[list[float]]:
    return _ef(texts)
