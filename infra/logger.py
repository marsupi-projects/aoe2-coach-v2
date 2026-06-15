"""
Structured step-level logger. Writes JSONL to logs/YYYY-MM-DD.jsonl.
One entry per event: run_start, tool_called, tool_result, run_end, run_error.
Consumed by the developer/operator for debugging and monitoring — not by the agent.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from config import LOGS_PATH

_MAX_RESULT_CHARS = 500


def _write(entry: dict) -> None:
    LOGS_PATH.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    path = LOGS_PATH / f"{date_str}.jsonl"
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def _entry(run_id: str, event: str, payload: dict) -> dict:
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "run_id": run_id,
        "event": event,
        **payload,
    }


def log_run_start(run_id: str, file_path: str, model: str) -> None:
    _write(_entry(run_id, "run_start", {"file_path": file_path, "model": model}))


def log_tool_called(run_id: str, tool_name: str, tool_input: dict) -> None:
    _write(_entry(run_id, "tool_called", {"tool": tool_name, "input": tool_input}))


def log_tool_result(run_id: str, tool_name: str, result: str, error: bool = False) -> None:
    _write(_entry(run_id, "tool_result", {
        "tool": tool_name,
        "result": result[:_MAX_RESULT_CHARS],
        "error": error,
    }))


def log_run_end(
    run_id: str,
    elapsed_seconds: float,
    evaluator_score: float,
    evaluator_passed: bool,
) -> None:
    _write(_entry(run_id, "run_end", {
        "elapsed_seconds": elapsed_seconds,
        "evaluator_score": evaluator_score,
        "evaluator_passed": evaluator_passed,
    }))


def log_run_error(run_id: str, error: str) -> None:
    _write(_entry(run_id, "run_error", {"error": error}))
