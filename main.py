"""Entrypoint for the aoe2-coach agent."""

from __future__ import annotations

import sys
from pathlib import Path

from core.agent import run


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python main.py <path/to/replay.aoe2record>", file=sys.stderr)
        sys.exit(1)

    file_path = sys.argv[1]
    if not Path(file_path).exists():
        print(f"Error: file not found: {file_path}", file=sys.stderr)
        sys.exit(1)

    result = run(file_path)

    # Blank line separates agent progress output from the final summary.
    print()
    if result["report_path"]:
        print(f"Report:  {result['report_path']}")
    print(f"Score:   {result['evaluator_score']:.3f} | Passed: {result['evaluator_passed']}")
    print(f"Run ID:  {result['run_id']}")
    print(f"Elapsed: {result['elapsed_seconds']}s")


if __name__ == "__main__":
    main()
