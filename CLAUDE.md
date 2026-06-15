# CLAUDE.md

## Project
This project follows the LLM Agent Blueprint defined in BLUEPRINT.md.
Always treat this document and SPEC.md as the two primary references for
every decision made during development. Read BLUEPRINT.md at the start of
every session before doing anything else.

## Architecture
The project uses the structure defined in BLUEPRINT.md. Do not deviate
from it without discussing it first. When in doubt about where something
belongs, consult BLUEPRINT.md before proceeding.

## Interaction rules
- Always read SPEC.md and BLUEPRINT.md before making architectural or
  behavioural decisions.
- Never make autonomous changes to the architecture without flagging them
  first and explaining why.
- When uncertain between two approaches, present both with a clear
  recommendation rather than picking one silently.
- Keep explanations concise unless asked to elaborate.
- Never commit or log credentials, even in examples or test files.
- If something is not covered by BLUEPRINT.md or SPEC.md, ask before
  proceeding.

## Database
- All database access goes through `core/database.py` exclusively.
- No other module connects to the database directly.
- Claude tools that touch the database must be narrow and explicit
  in `tools.py`.
- Never expose raw SQL through a tool definition.
- Database credentials live in `.env` only and flow through `config.py`.

## Python environment
- Always use a virtual environment. On any new project, create `.venv` before
  installing any dependencies:
  ```
  python -m venv .venv
  .venv\Scripts\Activate.ps1   # Windows
  source .venv/bin/activate     # Linux / Mac
  pip install -r requirements.txt
  ```
- Never install project dependencies into the global Python environment.
- `.venv/` must be in `.gitignore` from the start.

## Environment and deployment
- The project runs locally on Windows via Docker and on a remote VPS
  via the same Docker setup.
- `docker-compose.yml` must work identically in both environments.
- Environment-specific values go in `.env`, never hardcoded.
- `.env` is never committed. `.env.example` is always kept up to date.

## Code style for main.py and agent.py
Every step in `main.py` and `core/agent.py` must have:
- A `print()` statement that tells the user what is happening at that moment
  (e.g. starting a run, calling Claude, dispatching a tool, evaluating the report).
- A comment explaining the *why* of any non-obvious decision — a hidden constraint,
  a subtle invariant, or behaviour that would surprise a reader.

Apply this rule whenever either file is created or modified. Do not remove existing
prints or comments from these two files without an explicit instruction to do so.

## At the end of every session
Update `README.md` to reflect any changes made this session — new features, changed
commands, new output files, or anything that affects how someone sets up or runs the
project. Do not rewrite sections that have not changed.

Write a session summary to `journal/YYYY-MM-DD_session-NN.md` containing:
- What was discussed this session
- Decisions made and the reasoning behind them
- Things explicitly decided against and why
- Open questions to carry into the next session

Do not skip this step. The journal is the project memory across sessions.

After writing the journal entry, sync the Claude memory folder into `memory/` at
the project root. The Claude memory folder is the one defined in the system prompt
for this session. Copy every file from it into `memory/` so the project always
contains a version-controlled snapshot of the current memory state. Do not skip
this step either.
