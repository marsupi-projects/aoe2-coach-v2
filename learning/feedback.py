"""
Logs the outcome of each completed run to data/runs/ as a JSONL entry.
Captures the coaching report path, evaluator score, and all criteria results
so reflection.py can identify patterns across runs.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from config import RUNS_PATH


def log_run(
    run_id: str,
    replay_file: str,
    players: list[dict],
    coaching_report_path: str,
    evaluator_result: dict,
    prompt_version: str,
) -> Path:
    RUNS_PATH.mkdir(parents=True, exist_ok=True)
    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    path = RUNS_PATH / f"{date_str}.jsonl"

    entry = {
        "run_id": run_id,
        "timestamp": datetime.utcnow().isoformat(),
        "replay_file": replay_file,
        "players": players,
        "coaching_report_path": coaching_report_path,
        "evaluator_score": evaluator_result["score"],
        "evaluator_passed": evaluator_result["passed"],
        "criteria": evaluator_result["criteria"],
        "prompt_version": prompt_version,
    }

    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

    return path
