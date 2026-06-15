"""
Tracks evaluator scores grouped by prompt version to identify which version
performs best. Promotes the winner by printing it for review — manual promotion
into core/prompt.py prevents accidental regressions from auto-edits.
"""

from __future__ import annotations

from collections import defaultdict

from learning.reflection import load_run_history


def score_by_version(run_entries: list[dict]) -> dict[str, dict]:
    """
    Group scored runs by prompt_version and compute average score and pass rate.
    Returns: {version: {avg_score, pass_rate, run_count}}
    """
    scores: dict[str, list[float]] = defaultdict(list)
    passes: dict[str, int] = defaultdict(int)

    for entry in run_entries:
        score = entry.get("evaluator_score")
        if score is None:
            continue
        version = entry.get("prompt_version", "unknown")
        scores[version].append(score)
        if entry.get("evaluator_passed"):
            passes[version] += 1

    result = {}
    for version, version_scores in scores.items():
        n = len(version_scores)
        result[version] = {
            "avg_score": round(sum(version_scores) / n, 3),
            "pass_rate": round(passes[version] / n, 3),
            "run_count": n,
        }
    return result


def best_version(versions: dict[str, dict]) -> str | None:
    """Return the version with the highest average score, or None if empty."""
    if not versions:
        return None
    return max(versions, key=lambda v: versions[v]["avg_score"])


def tune() -> dict:
    """
    Load run history, compute scores per prompt version, and report the winner.
    Prints a promotion instruction when a clear winner exists.
    Returns the full analysis dict.
    """
    entries = load_run_history()
    versions = score_by_version(entries)

    if not versions:
        print("[prompt_tuner] No scored runs found — nothing to analyse.")
        return {"versions": {}, "best": None}

    winner = best_version(versions)
    print("[prompt_tuner] Score by prompt version:")
    for version, stats in sorted(versions.items()):
        marker = " <-- best" if version == winner else ""
        print(
            f"  {version}: avg={stats['avg_score']:.3f}  "
            f"pass_rate={stats['pass_rate']:.0%}  "
            f"n={stats['run_count']}{marker}"
        )

    if len(versions) == 1:
        # Only one version on record — useful as a baseline, nothing to compare yet.
        print(f"[prompt_tuner] Only one prompt version on record ({winner}) — baseline established.")
    else:
        print(f"[prompt_tuner] Best version: {winner}")
        print(f"[prompt_tuner] To promote: update PROMPT_VERSION in core/prompt.py to '{winner}'")

    return {"versions": versions, "best": winner}
