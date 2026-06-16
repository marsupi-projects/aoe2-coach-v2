---
name: project-decisions
description: "Key design decisions made for aoe2-coach-v2, including what was chosen and what was ruled out"
metadata: 
  node_type: memory
  type: project
  originSessionId: be345ee4-ec05-4370-8a49-5d517b220ef4
---

## Session 01 decisions (2026-06-14)

Decisions locked in as of session 01. All decisions below are implemented in code.

| Area | Decision |
|---|---|
| Civ knowledge seeding | ~~Organic~~ **REVERSED in session 08** — see session 08 decisions below |
| eAPM benchmarking | Relative only — compare player to their own past games; no hardcoded brackets |
| `get_player_history` | Batch variant (one call for multiple players, not one call per player) |
| `mgz` civ string | **Kjir fork pinned** — PyPI 1.8.51 and git master both fail on patch v101.103.47452.0+; `Kjir/aoc-mgz@b4a30d8` works; `parse_match()` used (returns civ as string); migration note in `requirements.txt` |
| Team history matching | Exact player combinations only (no partial matches) |
| Evaluator scoring | Rule-based; 1 point per §3 success criterion; score = n/11; ≥ 0.7 (8/11) passes |

**Evaluator note:** Will be replaced with LLM-as-judge in a future version once rule-based baseline is stable (SPEC.md §10).

## Session 03 decisions (2026-06-15)

| Area | Decision |
|---|---|
| Replay parser | `mgz.model.parse_match()` via Kjir fork (commit b4a30d8) — returns civ as string, eAPM, winner, profile_id for AI detection |
| AI detection | `profile_id == 0xFFFFFFFF` (4294967295) confirmed working via parse_match |
| Timeout check | `pending_tool_results` flag in `core/agent.py` — timeout only fires before a fresh API call, never when tool results are pending dispatch |
| First real run | Run 96ea6838: report written, all 7 tools called, evaluator not reached (timeout fix not yet in place); second attempt failed on network error |

## Session 04 decisions (2026-06-15)

| Area | Decision |
|---|---|
| Parser regex | `_extract_players` now handles multi-line format (`PLAYER N — name` + separate field lines); falls back from single-line if nothing matched |
| `limited_data` field | Added to `parse_replay` return (`has_ai` bool); fixes `_c9_data_limitations` evaluator criterion |
| Dummy ChromaDB data | Deleted `run-001` and `run-smoke-test` test fixtures |
| Report filenames | `{game_date}_{civs}_{map}_{result}_{analysis_date}.txt` via `build_report_filename()` in `tools.py`; `_last_parsed` module-level cache avoids changing tool API |
| Evaluator source | Reads report file directly (not `final_text`) — Claude's closing turn is a summary, not the report |
| Unicode arrows | Replaced `→` with `->` in print statements (Windows cp1252 can't encode U+2192) |
| README | Created; covers venv setup, `.env`, running `main.py`, output files, project structure |
| venv | Not yet created; user will set up `.venv` before next session |

**First clean full run:** `07f7232c` — Score 1.000 (PASS), 11/11, 245s

**Open items:**
- Set up `.venv` before next session
- Multiple runs of same replay in ChromaDB (96ea6838, e2747d6f, 07f7232c) — will inflate history until more replays added
- Test files not yet written (`tests/` per BLUEPRINT.md)

## Session 07 decisions (2026-06-17)

| Area | Decision |
|---|---|
| Reflection reports location | `data/reflections/` — not `logs/`; logs is for debug traces only; `REFLECTIONS_PATH` added to config |
| v1.3 validated | `reflect.py` ran against 7 real runs; 6 concrete conclusions produced; eAPM gap between players identified; v1.3 complete |
| v1.4 plan | ChromaDB switches from `PersistentClient` (file) to `HttpClient` (HTTP) when `CHROMA_HOST` env var is set; local dev unchanged; new files: `Dockerfile`, `docker-compose.yml`, `.dockerignore` |

**Why:** Deferring v1.4 to a fresh session — it touches `core/database.py` architecture and warrants a clean start.

## Session 08 decisions (2026-06-16)

| Area | Decision |
|---|---|
| Civ knowledge seeding | **Manual JSON files** — reversed session 01; organic seeding can't provide domain knowledge before many games have been played |
| Knowledge file format | JSON, one file per civ in `data/knowledge/civs/`; `_template.json` defines the schema |
| Civ schema | `civ`, `strengths`, `weaknesses`, `unique_unit`, `unique_tech` (nested by age), `economy_bonuses`, `team_bonus`, `build_order_notes`, `common_pairings`, `power_spikes` (nested by age) |
| Prompt tuner promotion | Manual only — BLUEPRINT said automatic but code was already manual; BLUEPRINT corrected, not the code |
| ingestion.py | Built in `memory/`; idempotent upsert; run via `python -m memory.ingestion` |
| prompt_tuner.py | `__main__` block added; run via `python -m learning.prompt_tuner` |

**Open items:**
- v1.4 (Docker) still pending — deferred from session 07, not touched this session
- Consider auto-calling ingestion at startup if knowledge files exist but aren't in ChromaDB yet
- Other knowledge types beyond civs? (map notes, build order guides)

## Session 02 decisions (2026-06-14)

| Area | Decision |
|---|---|
| Agentic loop | Manual loop (not SDK tool runner) — needed for per-tool logging, `tool_calls_seen` tracking, and timeout enforcement |
| Thinking | `thinking={"type": "adaptive"}` — supported by Sonnet 4.6, appropriate for multi-step replay reasoning |
| Model config | `CLAUDE_MODEL` from `config.py` (default `claude-sonnet-4-6`), overridable via `.env` |
| Tool errors | Caught per-tool, serialised as `"ERROR: ..."`, returned to Claude as `tool_result`; agent adapts gracefully |
| Logger | 5 event types: `run_start`, `tool_called`, `tool_result`, `run_end`, `run_error`; JSONL to `logs/YYYY-MM-DD.jsonl`; results truncated to 500 chars |
| Streaming | Not used in v1.1 — non-streaming simpler for local single-user tool; revisit if timeout issues arise |
| CLI | `sys.argv` direct access in `main.py` (no argparse); one positional argument |

**How to apply:** When adding new tools or modifying the loop, follow the per-tool error handling pattern. Tool result errors are never fatal — they are passed back to Claude for graceful handling.
