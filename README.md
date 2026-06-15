# aoe2-coach-v2

An LLM agent that analyses Age of Empires II replay files and produces structured coaching feedback. It parses a `.aoe2record` file, retrieves relevant history from a local vector database (ChromaDB), calls the Claude API to reason over the data, and writes a coaching report covering each human player and team synergy.

---

## Requirements

- Python 3.11+
- An Anthropic API key

---

## Installation

Create and activate a virtual environment, then install dependencies:

```powershell
# Create the venv (one time only)
python -m venv .venv

# Activate it (PowerShell — run this every time you open a new terminal)
.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

> `requirements.txt` pins `mgz` to a specific GitHub fork commit. This is intentional — the current PyPI release does not support replays from patch v101.103.47452.0+ (Last Chieftains DLC). See the comment in `requirements.txt` for the migration plan back to the official package.

The `.venv/` folder is already in `.gitignore` and will not be committed.

After installing dependencies, set up the pre-commit hook (one time per clone):

```bash
# Git Bash
cp scripts/pre-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

This copies the hook from `scripts/pre-commit` (tracked by git) into `.git/hooks/` (not tracked). It runs `pytest tests/` before every commit and blocks the commit if any test fails.

---

## Configuration

Copy `.env.example` to `.env` and fill in your API key:

```bash
cp .env.example .env
```

`.env` contents:

```
ANTHROPIC_API_KEY=sk-ant-...
CLAUDE_MODEL=claude-sonnet-4-6
CHROMA_PATH=data/chroma
RUNS_PATH=data/runs
REPORTS_PATH=data/reports
PROMPTS_PATH=data/prompts
REPLAYS_INBOX=data/replays/inbox
LOGS_PATH=logs
```

Only `ANTHROPIC_API_KEY` is required. All other values have working defaults and can be left as-is.

---

## Running the agent

Place your replay file anywhere accessible, then pass its path as the only argument:

```bash
python main.py "data\replays\inbox\MP Replay v101.103.47452.0 @2026.06.13 143618 (1).aoe2record"
```

The agent prints progress as it runs:

```
[07f7232c] Starting -> data\replays\inbox\MP Replay v101.103.47452.0 ...
[07f7232c] Calling Claude (turn 1) ...
[07f7232c]   -> parse_replay
[07f7232c]      OK
[07f7232c] Calling Claude (turn 2) ...
[07f7232c]   -> get_player_history
[07f7232c]      OK
[07f7232c]   -> get_team_history
[07f7232c]      OK
[07f7232c]   -> get_civ_knowledge
[07f7232c]      OK
[07f7232c]   -> get_civ_knowledge
[07f7232c]      OK
[07f7232c] Calling Claude (turn 3) ...
[07f7232c]   -> write_coaching_report
[07f7232c]      OK
[07f7232c] Calling Claude (turn 4) ...
[07f7232c]   -> write_run_entry
[07f7232c]      OK
[07f7232c]   -> store_run_memory
[07f7232c]      OK
[07f7232c] Calling Claude (turn 5) ...
[07f7232c] Agent done (stop_reason=end_turn)
[07f7232c] Evaluating report ...
[07f7232c] Score: 1.000 (PASS) in 245.39s

Report:  data\reports\20260613_byzantines-aztecs_wade_win_20260615.txt
Score:   1.000 | Passed: True
Run ID:  07f7232c-5f7e-4adc-92d4-2a56195b59af
Elapsed: 245.39s
```

A typical run takes 3–4 minutes (dominated by the Claude API call with adaptive thinking).

### Output files

| File | Description |
|---|---|
| `data/reports/YYYYMMDD_civs_map_result_YYYYMMDD.txt` | Coaching report — the main output |
| `data/runs/YYYY-MM-DD.jsonl` | Append-only run history |
| `data/chroma/` | ChromaDB vector store — player and team history |
| `logs/YYYY-MM-DD.jsonl` | Step-level structured log for debugging |

### Evaluator

Each run is scored against 11 criteria from `SPEC.md §3`. A score ≥ 0.7 (8/11) is a pass. The score is printed at the end of every run and stored in the run history.

---

## Running reflection and prompt tuner

After accumulating a few replays, run reflection to identify patterns and write conclusions into ChromaDB. The main agent picks them up automatically on the next run.

```powershell
python reflect.py
```

This calls two things in sequence:

1. **Reflection** — reads `data/runs/`, calls Claude to identify patterns across players, civs, and evaluator criteria, stores conclusions in ChromaDB, writes a markdown report to `logs/reflection_YYYY-MM-DD.md`
2. **Prompt tuner** — groups all scored runs by prompt version and reports which version performs best

A minimum of 3 scored runs is required for reflection to proceed. If you have fewer, it prints a skip message and exits cleanly.

---

## Running the tests

```powershell
python -m pytest tests/ -v
```

87 tests covering `core/parser.py`, `core/evaluator.py`, `core/database.py`, and `memory/retrieval.py`.
The database and retrieval tests use a temporary ChromaDB instance — production data is never touched.

**When to run them:**
- After editing any of the four modules above
- Before running `main.py` on a new replay if you have made recent code changes

There is no CI pipeline configured yet. Tests are run manually. A pre-commit hook or GitHub Actions workflow can be added later to run them automatically on every commit.

---

## Project structure

```
main.py              # Entrypoint — pass a replay file path
config.py            # All settings flow through here
core/
  agent.py           # Agentic loop — orchestrates tools and Claude API calls
  tools.py           # Tool definitions and implementations
  prompt.py          # System and task prompts
  parser.py          # Extracts structured data from Claude's report text
  evaluator.py       # Scores each run against SPEC.md §3
  database.py        # Single interface to ChromaDB
memory/
  retrieval.py       # RAG queries — player history, team history, civ knowledge
  episodic.py        # Stores run memories in ChromaDB after each run
  embeddings.py      # Text → vector utility
  memory.py          # Context window management
learning/
  feedback.py        # Logs run outcomes to data/runs/
infra/
  logger.py          # Structured JSONL step-level logging
data/
  replays/inbox/     # Drop replay files here
  reports/           # Coaching reports written here
  runs/              # JSONL run history
  chroma/            # ChromaDB on-disk store
logs/                # Step-level JSONL logs
journal/             # Development session notes (not runtime)
```

---

## Notes

- **One replay per run.** Pass one `.aoe2record` file per invocation. Batch processing and inbox auto-watching are planned for v2.1.
- **vs-AI games.** Feudal time, castle time, and resource stats are not available in vs-AI replay data. The agent detects this automatically and notes it in the report.
- **First run.** ChromaDB starts empty. There will be no player history on the first run — the agent states this explicitly in the report and builds history from subsequent runs.
