"""
Trigger reflection: analyse the run history, write conclusions to ChromaDB,
and produce a markdown report in logs/.

Usage:
    python reflect.py

Run this after accumulating a few games. The main agent (main.py) will
automatically pick up the stored conclusions on the next run.
"""

import sys

from learning.prompt_tuner import tune
from learning.reflection import reflect

print("=" * 60)
print("  REFLECTION")
print("=" * 60)

result = reflect()

if result["skipped"]:
    print(f"\nSkipped: only {result['runs_analyzed']} scored run(s) found.")
    print("Run more replays through main.py and try again.")
    sys.exit(0)

print(f"\nReport: {result['report_path']}")
print(f"Runs analysed: {result['runs_analyzed']}")

print()
print("=" * 60)
print("  PROMPT TUNER")
print("=" * 60)
tune()
