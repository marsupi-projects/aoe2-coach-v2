"""
Tests for memory/retrieval.py.

Uses the tmp_chroma fixture to isolate each test from production data.
The retrieval functions call core.database.query, which routes through the
patched _client, so no real ChromaDB data is read or written.
"""

import pytest
from core.database import upsert
from memory.retrieval import get_player_history, get_team_history, get_civ_knowledge


def seed_run(run_id, doc, metadata=None):
    upsert("runs", ids=[run_id], documents=[doc], metadatas=[metadata or {"source": "test"}])


def seed_civ(civ_id, doc, metadata=None):
    upsert("civ_knowledge", ids=[civ_id], documents=[doc], metadatas=[metadata or {"source": "test"}])


# ---------------------------------------------------------------------------
# get_player_history
# ---------------------------------------------------------------------------

class TestGetPlayerHistory:
    def test_empty_names_returns_empty(self, tmp_chroma):
        assert get_player_history([]) == []

    def test_empty_collection_returns_empty(self, tmp_chroma):
        assert get_player_history(["Frank"]) == []

    def test_returns_result_for_known_player(self, tmp_chroma):
        seed_run("r1", "Frank won with Britons on Arabia. eAPM 45.")
        results = get_player_history(["Frank"])
        assert len(results) >= 1
        assert any("Frank" in r["document"] for r in results)

    def test_result_has_expected_keys(self, tmp_chroma):
        seed_run("r1", "Frank played Britons.")
        results = get_player_history(["Frank"])
        assert "id" in results[0]
        assert "document" in results[0]
        assert "metadata" in results[0]

    def test_multiple_players_in_one_call(self, tmp_chroma):
        seed_run("r1", "Frank won with Britons on Arabia.")
        seed_run("r2", "Joris won with Franks on Arabia.")
        results = get_player_history(["Frank", "Joris"])
        docs = [r["document"] for r in results]
        assert any("Frank" in d for d in docs)
        assert any("Joris" in d for d in docs)


# ---------------------------------------------------------------------------
# get_team_history
# ---------------------------------------------------------------------------

class TestGetTeamHistory:
    def test_single_player_returns_empty(self, tmp_chroma):
        assert get_team_history(["Frank"]) == []

    def test_empty_collection_returns_empty(self, tmp_chroma):
        assert get_team_history(["Frank", "Joris"]) == []

    def test_returns_matching_team_game(self, tmp_chroma):
        seed_run("r1", "Frank and Joris teamed up on Black Forest. Both won.")
        results = get_team_history(["Frank", "Joris"])
        assert len(results) == 1
        assert "Frank" in results[0]["document"]
        assert "Joris" in results[0]["document"]

    def test_excludes_games_missing_one_player(self, tmp_chroma):
        seed_run("r1", "Frank played solo on Arabia.")
        results = get_team_history(["Frank", "Joris"])
        assert results == []

    def test_result_count_capped_at_n_results(self, tmp_chroma):
        for i in range(5):
            seed_run(f"r{i}", f"Frank and Joris played together on game {i}.")
        results = get_team_history(["Frank", "Joris"], n_results=2)
        assert len(results) <= 2


# ---------------------------------------------------------------------------
# get_civ_knowledge
# ---------------------------------------------------------------------------

class TestGetCivKnowledge:
    def test_empty_string_returns_empty(self, tmp_chroma):
        assert get_civ_knowledge("") == []

    def test_empty_collection_returns_empty(self, tmp_chroma):
        assert get_civ_knowledge("Britons") == []

    def test_returns_civ_document(self, tmp_chroma):
        seed_civ("britons-1", "Britons excel at archery with range bonus.")
        results = get_civ_knowledge("Britons")
        assert len(results) >= 1
        assert any("Britons" in r["document"] for r in results)

    def test_result_has_expected_keys(self, tmp_chroma):
        seed_civ("britons-1", "Britons have the best archers.")
        results = get_civ_knowledge("Britons")
        assert "id" in results[0]
        assert "document" in results[0]
        assert "metadata" in results[0]
