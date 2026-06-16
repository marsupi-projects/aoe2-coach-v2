"""
Tests for learning/reflection.py and learning/prompt_tuner.py.

The Claude API call inside reflect() is mocked so tests run offline.
ChromaDB storage uses the tmp_chroma fixture from conftest.py.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from learning.reflection import _format_entries, _write_report, load_run_history, reflect
from learning.prompt_tuner import best_version, score_by_version, tune


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_entry(
    run_id="aaaabbbb-0000-0000-0000-000000000000",
    timestamp="2026-06-16T10:00:00",
    score=1.0,
    passed=True,
    players=None,
    prompt_version="v1.0",
    criteria=None,
):
    if players is None:
        players = [
            {"name": "Alice", "civ": "Britons", "eapm": 40},
            {"name": "Bob", "civ": "Franks", "eapm": 55},
        ]
    if criteria is None:
        criteria = [{"name": "replay_parsed", "passed": True}]
    return {
        "run_id": run_id,
        "timestamp": timestamp,
        "replay_file": "game.aoe2record",
        "players": players,
        "evaluator_score": score,
        "evaluator_passed": passed,
        "criteria": criteria,
        "prompt_version": prompt_version,
    }


# ---------------------------------------------------------------------------
# load_run_history
# ---------------------------------------------------------------------------

class TestLoadRunHistory:
    def test_returns_empty_when_no_runs_dir(self, tmp_path, monkeypatch):
        import learning.reflection as mod
        monkeypatch.setattr(mod, "RUNS_PATH", tmp_path / "nonexistent")
        assert load_run_history() == []

    def test_reads_jsonl_entries(self, tmp_path, monkeypatch):
        import learning.reflection as mod
        monkeypatch.setattr(mod, "RUNS_PATH", tmp_path)
        entry = make_entry()
        (tmp_path / "2026-06-16.jsonl").write_text(
            json.dumps(entry) + "\n", encoding="utf-8"
        )
        result = load_run_history()
        assert len(result) == 1
        assert result[0]["run_id"] == entry["run_id"]

    def test_deduplicates_by_run_id_prefers_scored(self, tmp_path, monkeypatch):
        import learning.reflection as mod
        monkeypatch.setattr(mod, "RUNS_PATH", tmp_path)
        partial = {**make_entry(), "evaluator_score": None, "evaluator_passed": None}
        full = make_entry(score=0.9, passed=True)
        (tmp_path / "2026-06-16.jsonl").write_text(
            json.dumps(partial) + "\n" + json.dumps(full) + "\n", encoding="utf-8"
        )
        result = load_run_history()
        assert len(result) == 1
        assert result[0]["evaluator_score"] == 0.9

    def test_skips_malformed_lines(self, tmp_path, monkeypatch):
        import learning.reflection as mod
        monkeypatch.setattr(mod, "RUNS_PATH", tmp_path)
        (tmp_path / "2026-06-16.jsonl").write_text(
            "not valid json\n" + json.dumps(make_entry()) + "\n", encoding="utf-8"
        )
        result = load_run_history()
        assert len(result) == 1

    def test_reads_multiple_jsonl_files(self, tmp_path, monkeypatch):
        import learning.reflection as mod
        monkeypatch.setattr(mod, "RUNS_PATH", tmp_path)
        (tmp_path / "2026-06-14.jsonl").write_text(
            json.dumps(make_entry(run_id="run-a-" + "0" * 30)) + "\n", encoding="utf-8"
        )
        (tmp_path / "2026-06-15.jsonl").write_text(
            json.dumps(make_entry(run_id="run-b-" + "0" * 30)) + "\n", encoding="utf-8"
        )
        result = load_run_history()
        assert len(result) == 2


# ---------------------------------------------------------------------------
# _format_entries
# ---------------------------------------------------------------------------

class TestFormatEntries:
    def test_includes_run_id_prefix(self):
        entry = make_entry(run_id="abcd1234-0000-0000-0000-000000000000")
        output = _format_entries([entry])
        assert "abcd1234" in output

    def test_includes_score(self):
        entry = make_entry(score=0.727)
        output = _format_entries([entry])
        assert "0.727" in output

    def test_includes_player_names(self):
        output = _format_entries([make_entry()])
        assert "Alice" in output
        assert "Bob" in output

    def test_includes_failing_criteria(self):
        entry = make_entry(criteria=[
            {"name": "report_content", "passed": False},
            {"name": "replay_parsed", "passed": True},
        ])
        output = _format_entries([entry])
        assert "report_content" in output

    def test_handles_old_eapm_field_name(self):
        entry = make_entry(players=[{"name": "Alice", "civ": "Britons", "eAPM": 42}])
        output = _format_entries([entry])
        assert "Alice" in output

    def test_empty_list_returns_empty_string(self):
        assert _format_entries([]) == ""


# ---------------------------------------------------------------------------
# _write_report
# ---------------------------------------------------------------------------

class TestWriteReport:
    def test_creates_file(self, tmp_path, monkeypatch):
        import learning.reflection as mod
        monkeypatch.setattr(mod, "REFLECTIONS_PATH", tmp_path)
        path = _write_report("1. Pattern found.", [make_entry()], "reflection-id-001")
        assert path.exists()

    def test_file_contains_conclusions(self, tmp_path, monkeypatch):
        import learning.reflection as mod
        monkeypatch.setattr(mod, "REFLECTIONS_PATH", tmp_path)
        path = _write_report("1. eAPM is low.", [make_entry()], "reflection-id-001")
        assert "eAPM is low" in path.read_text(encoding="utf-8")

    def test_file_contains_player_names(self, tmp_path, monkeypatch):
        import learning.reflection as mod
        monkeypatch.setattr(mod, "REFLECTIONS_PATH", tmp_path)
        path = _write_report("conclusions", [make_entry()], "reflection-id-001")
        content = path.read_text(encoding="utf-8")
        assert "Alice" in content
        assert "Bob" in content


# ---------------------------------------------------------------------------
# reflect() — mocking the Claude API call
# ---------------------------------------------------------------------------

class TestReflect:
    def _mock_response(self, text="1. Pattern identified."):
        mock_msg = MagicMock()
        mock_msg.content = [MagicMock(text=text)]
        return mock_msg

    def test_skips_when_too_few_runs(self, tmp_path, monkeypatch, tmp_chroma):
        import learning.reflection as mod
        monkeypatch.setattr(mod, "RUNS_PATH", tmp_path)
        monkeypatch.setattr(mod, "REFLECTIONS_PATH", tmp_path / "reflections")
        result = reflect(min_runs=3)
        assert result["skipped"] is True
        assert result["runs_analyzed"] == 0

    def test_runs_with_enough_data(self, tmp_path, monkeypatch, tmp_chroma):
        import learning.reflection as mod
        monkeypatch.setattr(mod, "RUNS_PATH", tmp_path)
        monkeypatch.setattr(mod, "REFLECTIONS_PATH", tmp_path / "reflections")
        for i in range(3):
            (tmp_path / f"2026-06-1{i}.jsonl").write_text(
                json.dumps(make_entry(run_id=f"run-{i}-" + "0" * 29, score=1.0)) + "\n",
                encoding="utf-8",
            )
        with patch("learning.reflection.anthropic.Anthropic") as mock_cls:
            mock_cls.return_value.messages.create.return_value = self._mock_response()
            result = reflect(min_runs=3)
        assert result["skipped"] is False
        assert result["runs_analyzed"] == 3
        assert result["report_path"] is not None

    def test_stores_reflection_in_chroma(self, tmp_path, monkeypatch, tmp_chroma):
        import learning.reflection as mod
        monkeypatch.setattr(mod, "RUNS_PATH", tmp_path)
        monkeypatch.setattr(mod, "REFLECTIONS_PATH", tmp_path / "reflections")
        for i in range(3):
            (tmp_path / f"2026-06-1{i}.jsonl").write_text(
                json.dumps(make_entry(run_id=f"run-{i}-" + "0" * 29, score=1.0)) + "\n",
                encoding="utf-8",
            )
        with patch("learning.reflection.anthropic.Anthropic") as mock_cls:
            mock_cls.return_value.messages.create.return_value = self._mock_response(
                "1. Pattern stored."
            )
            reflect(min_runs=3)

        from core.database import get_all
        result = get_all("reflections")
        assert len(result["ids"]) == 1
        assert "Pattern stored" in result["documents"][0]


# ---------------------------------------------------------------------------
# score_by_version
# ---------------------------------------------------------------------------

class TestScoreByVersion:
    def test_groups_by_version(self):
        entries = [
            make_entry(score=1.0, passed=True, prompt_version="v1.0"),
            make_entry(run_id="b" * 36, score=0.8, passed=True, prompt_version="v1.0"),
            make_entry(run_id="c" * 36, score=0.9, passed=True, prompt_version="v1.1"),
        ]
        result = score_by_version(entries)
        assert "v1.0" in result
        assert "v1.1" in result
        assert result["v1.0"]["run_count"] == 2
        assert result["v1.1"]["run_count"] == 1

    def test_avg_score_correct(self):
        entries = [
            make_entry(score=1.0, passed=True, prompt_version="v1.0"),
            make_entry(run_id="b" * 36, score=0.8, passed=True, prompt_version="v1.0"),
        ]
        result = score_by_version(entries)
        assert result["v1.0"]["avg_score"] == 0.9

    def test_pass_rate_correct(self):
        entries = [
            make_entry(score=1.0, passed=True, prompt_version="v1.0"),
            make_entry(run_id="b" * 36, score=0.5, passed=False, prompt_version="v1.0"),
        ]
        result = score_by_version(entries)
        assert result["v1.0"]["pass_rate"] == 0.5

    def test_skips_entries_without_score(self):
        entries = [
            {**make_entry(), "evaluator_score": None},
            make_entry(run_id="b" * 36, score=1.0, passed=True),
        ]
        result = score_by_version(entries)
        assert result["v1.0"]["run_count"] == 1

    def test_empty_entries(self):
        assert score_by_version([]) == {}


# ---------------------------------------------------------------------------
# best_version
# ---------------------------------------------------------------------------

class TestBestVersion:
    def test_returns_highest_avg(self):
        versions = {
            "v1.0": {"avg_score": 0.8, "pass_rate": 0.8, "run_count": 5},
            "v1.1": {"avg_score": 0.9, "pass_rate": 0.9, "run_count": 3},
        }
        assert best_version(versions) == "v1.1"

    def test_returns_none_for_empty(self):
        assert best_version({}) is None

    def test_single_version(self):
        versions = {"v1.0": {"avg_score": 0.75, "pass_rate": 0.6, "run_count": 2}}
        assert best_version(versions) == "v1.0"
