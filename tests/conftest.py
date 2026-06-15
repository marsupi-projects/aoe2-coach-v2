"""
Shared pytest fixtures and environment setup.

ANTHROPIC_API_KEY must be set before config.py is imported anywhere in the
test session; setting it here at module level ensures conftest is processed
first by pytest.
"""

import os
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")

import pytest
import chromadb


@pytest.fixture
def tmp_chroma(tmp_path, monkeypatch):
    """
    Provides a temporary ChromaDB client that is isolated from production data.
    Patches core.database._client for the duration of each test that uses this
    fixture, then restores the original value.
    """
    import core.database as db
    original = db._client
    db._client = chromadb.PersistentClient(path=str(tmp_path / "chroma"))
    yield db._client
    db._client = original
