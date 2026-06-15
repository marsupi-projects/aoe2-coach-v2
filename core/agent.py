"""
Orchestration loop for the aoe2-coach agent.
Drives one replay analysis from prompt construction through evaluation and logging.
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime

import anthropic

from config import (
    ANTHROPIC_API_KEY,
    CLAUDE_MODEL,
    REPORTS_PATH,
    RUN_TIMEOUT_SECONDS,
)
from core.evaluator import evaluate
from core.parser import extract_report
from core.prompt import PROMPT_VERSION, SYSTEM_PROMPT, build_task_prompt, save_prompt_snapshot
from core.tools import TOOL_DEFINITIONS, build_report_filename, dispatch
from infra.logger import log_run_end, log_run_error, log_run_start, log_tool_called, log_tool_result
from learning.feedback import log_run
from memory.retrieval import get_reflections


def run(file_path: str) -> dict:
    run_id = str(uuid.uuid4())
    short_id = run_id[:8]  # display prefix — full ID goes to the JSONL log
    t_start = time.monotonic()

    print(f"[{short_id}] Starting -> {file_path}")

    # Retrieve recent reflections before building the prompt so Claude can use
    # accumulated patterns from past runs to make this report more specific.
    reflections = get_reflections(n=3)
    if reflections:
        print(f"[{short_id}] Loaded {len(reflections)} reflection(s) -> injecting into context")
    else:
        print(f"[{short_id}] No reflections found yet (run reflect.py after a few games)")

    task_prompt = build_task_prompt(file_path, run_id, reflections=reflections or None)
    save_prompt_snapshot(SYSTEM_PROMPT, task_prompt, run_id)

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    log_run_start(run_id, file_path, CLAUDE_MODEL)
    messages: list[dict] = [{"role": "user", "content": task_prompt}]

    final_text = ""
    tool_calls_seen: set[str] = set()  # used by run_meta to verify write tools fired
    parsed_data: dict = {}

    try:
        # Only check timeout before a fresh API call with no pending tool results.
        # If the previous response contained tool_use blocks, we must respond to them
        # regardless of elapsed time — the timeout must not interrupt mid-chain work.
        pending_tool_results = False
        turn = 0

        while True:
            if not pending_tool_results and time.monotonic() - t_start > RUN_TIMEOUT_SECONDS:
                raise TimeoutError(f"Run {run_id} exceeded {RUN_TIMEOUT_SECONDS}s timeout")

            turn += 1
            print(f"[{short_id}] Calling Claude (turn {turn}) ...")

            response = client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=16000,
                thinking={"type": "adaptive"},
                system=SYSTEM_PROMPT,
                tools=TOOL_DEFINITIONS,
                messages=messages,
            )

            tool_use_blocks = [b for b in response.content if b.type == "tool_use"]
            text_blocks = [b for b in response.content if b.type == "text"]

            if text_blocks:
                final_text = text_blocks[-1].text

            messages.append({"role": "assistant", "content": response.content})

            # Set before the break check so the next iteration skips the timeout
            # guard when there are tool results still waiting to be sent back.
            pending_tool_results = bool(tool_use_blocks)

            if response.stop_reason == "end_turn" or not tool_use_blocks:
                print(f"[{short_id}] Agent done (stop_reason={response.stop_reason})")
                break

            tool_results = []
            for tool in tool_use_blocks:
                tool_calls_seen.add(tool.name)
                log_tool_called(run_id, tool.name, tool.input)
                print(f"[{short_id}]   -> {tool.name}")
                try:
                    result = dispatch(tool.name, tool.input)
                    # Capture parse_replay output directly from the dict result rather
                    # than re-parsing the message history — keeps evaluator input clean.
                    if tool.name == "parse_replay" and isinstance(result, dict):
                        parsed_data = result
                    content = result if isinstance(result, str) else str(result)
                    log_tool_result(run_id, tool.name, content)
                    print(f"[{short_id}]      OK")
                except Exception as exc:
                    content = f"ERROR: {exc}"
                    log_tool_result(run_id, tool.name, content, error=True)
                    print(f"[{short_id}]      ERROR: {exc}")

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool.id,
                    "content": content,
                })

            messages.append({"role": "user", "content": tool_results})

        elapsed = round(time.monotonic() - t_start, 2)
        analysis_date = datetime.utcnow().strftime("%Y%m%d")
        filename = build_report_filename(parsed_data, analysis_date) if parsed_data else f"{run_id}.txt"
        report_path = REPORTS_PATH / filename

        # tool_calls_seen tracks which write tools Claude actually invoked so the
        # evaluator can verify persistence without re-walking the message history.
        run_meta = {
            "report_path_exists": report_path.exists(),
            "run_entry_written": "write_run_entry" in tool_calls_seen,
            "chroma_stored": "store_run_memory" in tool_calls_seen,
            "elapsed_seconds": elapsed,
        }

        print(f"[{short_id}] Evaluating report ...")
        # Read the written file as the source of truth for evaluation.
        # final_text is Claude's closing turn summary, not the coaching report itself —
        # the report is written by the write_coaching_report tool in an earlier turn.
        if report_path.exists():
            report_source = report_path.read_text(encoding="utf-8")
        else:
            report_source = final_text
        parsed_report = extract_report(report_source)
        evaluator_result = evaluate(parsed_data, parsed_report, run_meta)

        # is_human defaults to True as a safe fallback if parse_replay errored and
        # parsed_data is empty — avoids silently dropping all players from feedback.
        players = parsed_data.get("players", [])
        human_players = [p for p in players if p.get("is_human", True)]

        log_run(
            run_id=run_id,
            replay_file=file_path,
            players=human_players,
            coaching_report_path=str(report_path) if run_meta["report_path_exists"] else "",
            evaluator_result=evaluator_result,
            prompt_version=PROMPT_VERSION,
        )

        log_run_end(run_id, elapsed, evaluator_result["score"], evaluator_result["passed"])

        passed_str = "PASS" if evaluator_result["passed"] else "FAIL"
        print(f"[{short_id}] Score: {evaluator_result['score']:.3f} ({passed_str}) in {elapsed}s")

        return {
            "run_id": run_id,
            "elapsed_seconds": elapsed,
            "evaluator_score": evaluator_result["score"],
            "evaluator_passed": evaluator_result["passed"],
            "report_path": str(report_path) if run_meta["report_path_exists"] else None,
            "players": human_players,
        }

    except Exception as exc:
        elapsed = round(time.monotonic() - t_start, 2)
        log_run_error(run_id, str(exc))
        print(f"[{short_id}] FAILED after {elapsed}s: {exc}")
        raise
