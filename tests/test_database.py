"""
Tests for core/database.py.

Uses the tmp_chroma fixture (from conftest.py) to run against a temporary
on-disk ChromaDB instance so production data is never touched.
"""

import pytest
from core.database import get_collection, upsert, query


class TestGetCollection:
    def test_returns_collection(self, tmp_chroma):
        col = get_collection("test_col")
        assert col is not None

    def test_get_or_create_idempotent(self, tmp_chroma):
        col1 = get_collection("idempotent_col")
        col2 = get_collection("idempotent_col")
        assert col1.name == col2.name


class TestUpsert:
    def test_upsert_adds_documents(self, tmp_chroma):
        upsert("runs", ids=["r1"], documents=["Frank played Britons."], metadatas=[{"player": "Frank"}])
        col = get_collection("runs")
        assert col.count() == 1

    def test_upsert_overwrites_same_id(self, tmp_chroma):
        upsert("runs", ids=["r1"], documents=["v1"], metadatas=[{"v": "1"}])
        upsert("runs", ids=["r1"], documents=["v2"], metadatas=[{"v": "2"}])
        assert get_collection("runs").count() == 1

    def test_upsert_multiple_documents(self, tmp_chroma):
        upsert("runs",
               ids=["a", "b", "c"],
               documents=["doc a", "doc b", "doc c"],
               metadatas=[{"i": "0"}, {"i": "1"}, {"i": "2"}])
        assert get_collection("runs").count() == 3


class TestQuery:
    def test_empty_collection_returns_empty_lists(self, tmp_chroma):
        result = query("empty_col", query_texts=["anything"])
        assert result["ids"] == [[]]
        assert result["documents"] == [[]]
        assert result["metadatas"] == [[]]

    def test_query_returns_inserted_document(self, tmp_chroma):
        upsert("runs", ids=["r1"], documents=["Frank won with Britons on Arabia."], metadatas=[{"player": "Frank"}])
        result = query("runs", query_texts=["Frank Britons"], n_results=1)
        assert len(result["ids"][0]) == 1
        assert result["ids"][0][0] == "r1"

    def test_n_results_capped_at_collection_size(self, tmp_chroma):
        upsert("runs", ids=["r1"], documents=["doc1"], metadatas=[{"source": "test"}])
        result = query("runs", query_texts=["doc"], n_results=10)
        # Collection has 1 document so ChromaDB can return at most 1
        assert len(result["ids"][0]) == 1

    def test_metadata_returned(self, tmp_chroma):
        upsert("runs", ids=["r1"], documents=["doc"], metadatas=[{"player": "Frank"}])
        result = query("runs", query_texts=["doc"], n_results=1)
        assert result["metadatas"][0][0]["player"] == "Frank"
