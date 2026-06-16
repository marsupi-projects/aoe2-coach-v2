# BLUEPRINT.md
# LLM Agent Blueprint

---

## Version overview

### v1 — Shared foundation

- **v1.1 — On-demand LLM agent** — the core loop working end to end: the agent calls the Claude model, uses tools, parses output, triggered by running a script manually.
- **v1.2 — + Persistence** — the agent now remembers things between runs: ChromaDB stores embeddings, `data/runs/` keeps the raw history, `logs/` keeps the human-readable version.
- **v1.3 — + Self-improvement** — the agent gets better over time: the evaluator scores each run, feedback logs the signal, and reflection distils patterns back into memory.
- **v1.4 — + Docker** — agent and ChromaDB become two containers in a single `docker-compose.yml`; the stack can now be spun up on any VPS with one command.
- **v1.5 — + CI/CD** — a GitHub Actions workflow runs the test suite on every push (CI); if tests pass, the workflow SSHs into the VPS, pulls the latest code, and restarts the Docker stack automatically (CD); no manual deployment steps required from this point on.

### v2 — Autonomous path

- **v2.1 — Autonomous LLM agent** — the agent runs without you: a cron job triggers the container on a schedule; Docker ensures it restarts automatically if it crashes or the VPS reboots.
- **v2.2 — LLM agent service** — the agent becomes reachable: a FastAPI container is added to `docker-compose.yml`, exposing an API so other systems can trigger runs, check status, and read output.
- **v2.3 — LLM subagent** — the agent becomes a specialist: the API contract is cleaned up and documented so an orchestrator can call it as one tool among many; the container is now independently deployable.

### v3 — Interactive path

- **v3.1 — Interactive LLM agent** — the human joins the loop: the agent processes a turn, responds, then waits; session state is persisted in a volume so conversations survive container restarts.
- **v3.2 — Chatbot / copilot** — the agent gets a face: a frontend container is added to `docker-compose.yml` alongside the agent and ChromaDB, giving users a chat UI with streaming responses and persistent chat history.

---

## Key concepts

- **Orchestration** — the logic in `agent.py` that coordinates every other module in the right sequence. It assembles context, calls the Claude model, intercepts tool call requests, executes the corresponding functions, passes results back to the Claude model, and keeps the loop running until the Claude model produces a final answer. Orchestration is what makes the agent feel autonomous — it reasons and acts without human intervention between steps.

- **RAG (Retrieval Augmented Generation)** — the practice of fetching relevant information from a knowledge base and injecting it into the prompt so the Claude model can reason over it. Instead of relying solely on what the Claude model was trained on, RAG lets the agent pull in specific, up-to-date, task-relevant context at runtime. In this architecture, `retrieval.py` handles RAG by querying ChromaDB and returning the most semantically similar content to the current task.

- **The agentic loop** — the repeating cycle of reason → act → observe → reason again that happens inside `agent.py` when the Claude model makes multiple tool calls in a single run. The Claude model reasons about the task, requests a tool, receives the result, reasons again, and may request another tool — all before producing a final answer. This is what distinguishes an agent from a simple one-shot call to the Claude model.

- **Token limits** — the Claude model can only process a certain amount of text in one call. This is why `memory.py` actively manages what gets passed in, and why `episodic.py` stores compressed summaries rather than full run histories. RAG also helps by retrieving only the most relevant context rather than passing everything at once.

- **Structured output** — the Claude model returns natural language by default. `parser.py` exists because the rest of the system needs predictable, structured data it can act on. Making the Claude model return structured output reliably is a prompt engineering challenge that lives in `prompt.py` and is validated by `test_parser.py`.

- **Vector search** — ChromaDB does not search by keyword; it searches by semantic similarity between vectors. This means `retrieval.py` can find relevant past runs even if they use completely different words than the current task. The quality of retrieval depends directly on the quality of the embedding model wrapped in `embeddings.py`.

- **Run** — a single execution of the agent from start to finish. One trigger → one complete agentic loop → one result. `data/runs/` tracks runs. This is the core runtime unit.

- **Step** — what happens inside a single run. Each time the Claude model reasons, calls a tool, receives a result, and reasons again is one step. A single run can contain multiple steps. `logger.py` logs at the step level — granular enough to debug exactly where something went wrong inside a run.

- **Session** — a development concept, not a runtime concept. A session is one sitting in Claude Code where you work on the project. It starts when you open the IDE and ends when you close it. `journal/` tracks sessions. Sessions have no direct relationship to runs or steps — they belong to a different layer entirely.

- **`journal/` vs `logger.py` output** — both are written for you to read, but they capture completely different things. `journal/` is written by Claude Code at the end of a development session; it captures what was discussed, decided, and left open during development — the why behind decisions. `logger.py` output is written by the agent at runtime during every run, at the step level; it captures technical execution details for debugging and operational monitoring. `journal/` is about building the agent. `logger.py` is about the agent running. The agent itself never reads either.

---

## V1 architecture

### Root files — the foundation of the project, everything starts here.

- **`SPEC.md`** — defines what the agent is supposed to do, what success looks like, and what the constraints are; this is the reference point for every decision made during development and every score produced at runtime.
- **`BLUEPRINT.md`** — this file; the architectural reference for the project covering version overview, key concepts, module descriptions, and how everything interacts.
- **`CLAUDE.md`** — instructions for Claude Code during development sessions; defines how Claude Code should interact, what conventions to follow, what never to do without asking, and how to write the session summary to `journal/` at the end of every session.
- **`README.md`** — how to set up and run the project; written for yourself or anyone else returning to the project after a break.
- **`main.py`** — the entrypoint; the single file you run to start the agent.
- **`config.py`** — all settings; API keys, model names, file paths, thresholds, and database connection details all flow through here.
- **`.env`** — secrets and credentials, never committed to Git; each environment (laptop, VPS) maintains its own copy.
- **`.env.example`** — committed to Git, shows the required keys without values so any environment knows exactly what its `.env` needs to contain.
- **`.gitignore`** — ensures `.env`, `data/`, and other sensitive or generated files never accidentally get committed.
- **`Dockerfile`** — containerises the agent so it runs identically on your Windows laptop and on the VPS.
- **`docker-compose.yml`** — runs the agent and ChromaDB together as one stack; one command spins up the entire system in any environment.
- **`requirements.txt` or `pyproject.toml`** — pins the exact dependency versions the agent needs to run.

---

### `core/` — the brain of the agent, the code that runs on every single cycle.

- **`agent.py`** — the orchestration loop; pulls context, calls the Claude model, intercepts tool call requests, executes them, passes results back to the Claude model, and keeps the agentic loop running until a final answer is produced.
- **`prompt.py`** — the prompts sent to the Claude model via the API; includes the system prompt that defines the Claude model's role, the task prompt that describes what it needs to do on each run, and templates used to structure input before sending; kept separate from logic so prompts can be tuned without touching code, and versioned snapshots are written to `data/prompts/`.
- **`evaluator.py`** — scores and self-critiques each run against the criteria defined in `SPEC.md`; the output of this is what makes the agent improvable over time.
- **`tools.py`** — defines what actions the Claude model is allowed to request, including narrow and explicit database queries; also contains the implementations that `agent.py` executes when the Claude model requests a tool; the Claude model never executes tools directly, it requests them and `agent.py` executes them.
- **`parser.py`** — extracts structured output from the Claude model's responses; turns raw text into data the rest of the system can work with.
- **`database.py`** — the single interface between the agent and your database; every module that needs database access goes through here, keeping connection logic and credentials in one place.

---

### `memory/` — everything the agent knows, both within a run and across runs.

- **`memory.py`** — reads and writes the context window; manages what gets passed to the Claude model on each call to stay within token limits.
- **`retrieval.py`** — queries ChromaDB using RAG to fetch the most semantically relevant past context, run summaries, and knowledge before each call to the Claude model.
- **`ingestion.py`** — handles storing new incoming external data into ChromaDB; things that arrive from outside the agent's own reasoning — database content, external documents, raw inputs; calls `embeddings.py` to convert that data into vectors before storing.
- **`episodic.py`** — handles storing the agent's own memories of what it did; after each run, takes the run summary and writes it to ChromaDB as a compressed memory the agent can retrieve later; calls `embeddings.py` under the hood but stores the agent's own experience, not external data.
- **`embeddings.py`** — a utility wrapper around the embedding model that knows nothing about what is being stored or why; its only job is to take any piece of text and convert it into a vector; used by both `ingestion.py` and `episodic.py` and keeps the embedding model swappable without touching the rest of the memory layer.

---

### `learning/` — where the agent gets better, the self-improvement loop that separates this from a simple script.

- **`feedback.py`** — logs the outcome of each complete run to `data/runs/`: what the Claude model returned, the score `evaluator.py` assigned, and any real-world signals about whether the run succeeded; broader than just the Claude model's response — it captures how well the entire run went.
- **`reflection.py`** — periodically queries `data/runs/` using RAG to identify patterns across recent runs, writes conclusions back into ChromaDB as updated beliefs, and produces a human-readable report in `data/reflections/`.
- **`prompt_tuner.py`** — tracks which prompt variants in `data/prompts/` score higher over time and promotes winners back to `prompt.py`; over time the agent converges on better prompts automatically.

---

### `infra/` — the VPS runtime layer, everything the agent needs to live reliably on a server.

- **`scheduler.py`** — cron and trigger logic; present in v1 but not yet active, ready for v2.1 when the agent goes autonomous.
- **`logger.py`** — writes structured JSONL logs at the step level during every run; consumed by you as the developer and operator when debugging or monitoring the agent on the VPS, not by the agent itself.
- **`health.py`** — heartbeat endpoint; lets VPS monitoring know the agent is alive and responding.

---

### `tests/` — ensures individual modules behave correctly as the agent grows.

- **`test_parser.py`** — verifies that structured output is correctly extracted from a range of Claude model responses.
- **`test_evaluator.py`** — checks that scoring logic produces consistent results against known inputs.
- **`test_retrieval.py`** — confirms that ChromaDB queries return relevant results and handle edge cases.
- **`test_database.py`** — validates that database queries and writes behave correctly without touching production data.

Tests are run with `pytest`. A git pre-commit hook runs the full suite before every commit and blocks the commit if any test fails. The hook source lives at `scripts/pre-commit` (tracked by git) and must be copied to `.git/hooks/pre-commit` once per clone — see `README.md` for the exact command. See `SPEC.md §12` for the full testing and CI specification, including the deferred GitHub Actions improvement.

---

### Data and logs — the persistent layer, everything the agent writes and reads between runs.

- **`data/chroma/`** — ChromaDB on-disk store; the vector database the agent reads from and writes to on every run.
- **`data/runs/`** — append-only JSONL run history; the source of truth for every run the agent has ever performed; read by `reflection.py` and `prompt_tuner.py`.
- **`data/prompts/`** — versioned prompt snapshots; tracks which prompt was active when so results can always be traced back to a specific version.
- **`data/reflections/`** — human-readable reflection reports written by `reflection.py`; one markdown file per reflection run, meant for you to read and review.
- **`journal/`** — development session summaries written by Claude Code at the end of every session; records what was discussed, decided, and left open; development memory, not runtime memory.

---

## How the components interact

Every run begins in `main.py`, which hands control to `agent.py`. This is where orchestration lives — `agent.py` is the conductor that coordinates every other module in the right sequence, makes decisions about what to do next, and keeps the run moving until it reaches a conclusion.

Before touching the Claude model, `agent.py` calls `memory.py` to assemble context for the current run. `memory.py` triggers `retrieval.py`, which uses RAG — Retrieval Augmented Generation, the practice of fetching relevant information from a knowledge base and injecting it into the prompt so the Claude model can reason over it — to query ChromaDB and pull in the most semantically relevant past run summaries, beliefs from previous reflections, and any domain knowledge previously ingested. If the task requires data from your database, `agent.py` calls `database.py` to fetch it. All of this context, combined with the current task, is shaped into a prompt by `prompt.py` and sent to the Claude model via the API along with the tool definitions from `tools.py`.

The Claude model's response comes back either as a final answer or a tool call request. If the Claude model wants to use a tool, `agent.py` intercepts that request, executes the corresponding function in `tools.py` — which may call `database.py` or `retrieval.py` — and passes the result back to the Claude model. This is the agentic loop: reason → act → observe → reason again. It can repeat multiple times within a single run. `agent.py` keeps orchestrating until the Claude model produces a final answer, at which point `parser.py` extracts the structured output.

Once the run completes, `evaluator.py` scores the output against the criteria in `SPEC.md` and passes that signal to `feedback.py`, which appends a JSONL entry to `data/runs/` capturing the Claude model's output, the score, and any real-world outcome signals. Anything new the agent learned gets embedded by `embeddings.py` — converted into a vector, a numerical representation that captures semantic meaning and makes content searchable by similarity rather than exact keywords — and stored in ChromaDB via `ingestion.py` if it is external knowledge, or via `episodic.py` if it is a memory of what the agent itself did. Periodically, `reflection.py` uses RAG to query `data/runs/` for patterns across recent runs, distils conclusions, writes updated beliefs back into ChromaDB, and produces a markdown report in `logs/`. `prompt_tuner.py` watches scores across `data/prompts/` and surfaces better-performing variants back to `prompt.py`. Throughout all of this, `logger.py` records each step as structured JSONL for your operational monitoring, `health.py` signals the system is alive, and `config.py` is the single source of truth for every setting every module touches.
