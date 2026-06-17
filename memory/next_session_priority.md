---
name: next-session-priority
description: First thing next session — continue Docker setup after WSL 2 install + laptop restart
metadata: 
  node_type: memory
  type: project
  originSessionId: 983c2a0e-4b41-4f4c-98b4-4555b145d7ae
---

Docker setup (v1.4) is mid-flight. All files are written and committed. Stopped because WSL 2 was not installed — `wsl --install` was run and a laptop restart is required to complete it.

**Pick up here:**
1. After restart, WSL 2 finishes setup automatically (a terminal may pop up — let it complete)
2. Start Docker Desktop, wait for whale icon to go steady
3. `docker compose build` — builds the agent image
4. `docker compose up chromadb -d` — starts ChromaDB in background
5. Test a run: `docker compose run agent python main.py "data/replays/inbox/your_replay.aoe2record"`

**Why:** v1.4 is the Docker milestone — agent and ChromaDB as two containers, stack deployable on any VPS with one command.
