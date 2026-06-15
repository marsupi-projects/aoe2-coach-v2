# SPEC.md
# Agent Specification

---

## 1. Agent identity

**Name:** aoe2-coach-v2

**Purpose:** Analyses Age of Empires II game replay files (.aoe2record) and produces structured coaching feedback for human players, including individual performance and team synergy where multiple human players are present; does not play, simulate, or modify games.

---

## 2. Task description

**What the agent does on each run:**

The agent receives a .aoe2record replay file, parses it using the `mgz` library (PyPI release), and extracts whatever data the parser exposes. It then retrieves relevant past run summaries from ChromaDB — previous games by the same player(s), patterns identified by earlier reflection cycles, and any domain knowledge previously ingested — and uses all of this as context to call the Claude model. The Claude model reasons over the replay data and historical context to produce a coaching report. The report must explicitly reference comparable past games for each human player, or state clearly that no comparable past games were found. When two or more human players are on the same team, the report must also include a team synergy section analysing how well they play together — based on civ composition compatibility in the current game, and on win/loss patterns, eAPM balance, and civ pairing history across past games where the same players appeared together. If this is the first game on record with this player combination, that must be stated explicitly. The report is evaluated, stored, and used to update the agent's memory so that future runs are informed by accumulated patterns.

**What a completed run looks like:**

By the time a run finishes successfully: the replay has been parsed without error; a coaching report has been produced covering all human players and the available data fields (civilisation, eAPM, game duration, winner/loser, team composition); the report includes a historical context section per player and, where applicable, a team synergy section; the report has been scored by `evaluator.py`; a JSONL entry has been appended to `data/runs/`; the run summary has been embedded and stored in ChromaDB via `episodic.py`; and a coaching report written to `data/reports/` as a .txt file.

---

## 3. Success criteria

- [ ] Replay parsed without error; `parse_replay` returns a valid dict with no exception
- [ ] All human players identified correctly (AI players filtered out by `user_id == 0xFFFFFFFF` sentinel)
- [ ] Coaching report covers every human player individually — no player is omitted
- [ ] Civilisation names resolved correctly for all players (no raw `civ_NN` fallbacks in output)
- [ ] Coaching report produced containing at least: player name, civ, eAPM, win/loss, and at least three concrete observations or recommendations per human player
- [ ] Report contains a historical context section for each human player: either references at least one comparable past game by name/date, or explicitly states "No previous games on record for [player]"
- [ ] When two or more human players are on the same team: report contains a team synergy section covering civ composition compatibility for the current game, and win/loss pattern and civ pairing history for this player combination across past games; or explicitly states this is the first game on record with this combination
- [ ] When only one human player is present (solo vs AI): team synergy section is omitted with no mention required
- [ ] Report acknowledges data limitations clearly when running on a custom lobby / vs-AI game (no fabricated feudal time, castle time, or resource stats)
- [ ] Coaching report written as a .txt file to `data/reports/`
- [ ] Run entry appended to `data/runs/` with valid JSONL
- [ ] Run summary embedded and stored in ChromaDB without error
- [ ] Evaluator score ≥ 0.7 out of 1.0

---

## 4. Failure criteria

- [ ] Parser raises an exception or returns an empty/malformed dict
- [ ] Coaching report is empty, covers only some human players, contains only generic advice unrelated to the actual replay data, or fabricates stats not present in the parser output (e.g. invents a feudal time for a vs-AI game)
- [ ] Any human player's civilisation is reported as `civ_NN` (raw ID fallback)
- [ ] AI players misclassified as human players in the coaching output
- [ ] Historical context section absent — report neither references past games nor explicitly states none were found
- [ ] Two or more human players on the same team but team synergy section entirely absent (a "no history found" statement is acceptable; silence is not)
- [ ] Coaching report not written to `data/reports/` as a .txt file
- [ ] Run entry not written to `data/runs/` or ChromaDB write fails silently
- [ ] Run exceeds 120 seconds wall-clock time
- [ ] Evaluator score < 0.5 out of 1.0

---

## 5. Inputs

**What the agent receives at the start of each run:**
One .aoe2record file path provided by the user via CLI argument or placed in a designated `data/replays/inbox/` folder. On autonomous runs (v2.1+), the scheduler watches that folder and triggers a run for each new file.

**Where it comes from:**
Manual file drop by the user. Future: automated pickup from `data/replays/inbox/`.

**Example input:**
```
data/replays/inbox/2025-06-10_frank_vs_ai.aoe2record
```

---

## 6. Outputs

**What the agent produces at the end of each run:**

1. **Coaching report (.txt)** — plain text file written to `data/reports/YYYY-MM-DD_run-NN.txt`. Sections: Game summary; per-player blocks (name, civ, eAPM, win/loss, historical context, observations, recommendations); Team synergy (present only when two or more human players share a team — covers civ composition compatibility for this game and win/loss + civ pairing history for this combination across past games, or explicit statement that this is the first game on record together); Data limitations note (present whenever feudal/castle/resource stats are unavailable).
2. **JSONL run entry** — appended to `data/runs/YYYY-MM-DD.jsonl`; fields: `run_id`, `timestamp`, `replay_file`, `players`, `parsed_data`, `coaching_report_path`, `evaluator_score`, `prompt_version`.
3. **ChromaDB memory entry** — run summary embedded and stored via `episodic.py` for future retrieval.

**Where it goes:**
`data/reports/` (coaching report), `data/runs/` (JSONL), ChromaDB (`data/chroma/`). The coaching report path is also printed to stdout.

**Example output (coaching report excerpt):**
```
GAME SUMMARY
------------
Duration: 28m 14s | Map: Arabia | Game type: Custom lobby vs AI
Human players: Frank (team 1), Joris (team 1) vs AI


PLAYER: Frank | Britons | eAPM: 42 | Result: Loss
--------------------------------------------------

Historical context:
  Previous game (2025-05-28): Frank played Franks, lost in 31m, eAPM 39.
  Previous game (2025-06-01): Frank played Britons, lost in 45m, eAPM 44.
  Pattern: two consecutive losses with similar eAPM — no improvement trend yet.

Observations:
  - eAPM of 42 is slightly higher than your last game (39) but consistent
    with your recent range.
  - You have now played Britons twice; both games ended in a loss.
  - Game ended under 30 minutes, matching the short-game loss from 2025-05-28.

Recommendations:
  - Focus on villager production in the first 10 minutes before military.
  - Practice dark-age build orders for Britons — both Britons games ended early.


PLAYER: Joris | Franks | eAPM: 61 | Result: Loss
-------------------------------------------------

Historical context:
  No previous games on record for Joris.

Observations:
  - eAPM of 61 is healthy and suggests good mechanical activity.
  - Franks are a cavalry civilisation; strong in castle age but slow to feudal.
  - Despite higher eAPM than teammate Frank, the game was still lost early.

Recommendations:
  - Co-ordinate feudal timing with your teammate to avoid being caught separately.
  - Consider a faster feudal build given how short this game was.


TEAM SYNERGY: Frank + Joris
----------------------------

Current game:
  Britons (Frank) + Franks (Joris) is a mixed composition. Britons favour
  archers, Franks favour cavalry. These civs do not conflict but require
  deliberate lane-splitting to work well together.

Together across past games:
  Previous game (2025-06-01): Frank (Britons) + Joris (Persians), Loss, 45m.
  Record together: 0 wins, 1 loss from 1 game on record.
  Pattern: too few games to draw conclusions — revisit after 3+ games together.


DATA LIMITATIONS
----------------
This was a custom lobby / vs-AI game. Feudal time, castle time, and resource
collection stats are not available. Coaching is based on eAPM, civilisation,
and game duration only.
```

---

## 7. Tools

- **`parse_replay(file_path)`** — parse a .aoe2record file using `mgz.summary.Summary` (PyPI release); return structured dict with all players, eAPM per player, civilisations, duration, winner flags, and a `note` field describing any data limitations
- **`get_player_history(player_name)`** — retrieve past run summaries for a named player from ChromaDB; returns a list of past games (date, civ, eAPM, result, duration); returns an empty list if no past games exist
- **`get_team_history(player_names)`** — retrieve past games where all named players appeared on the same team; returns a list of past games (date, civs, result, duration) for use in the team synergy section; returns an empty list if no shared games exist
- **`get_civ_knowledge(civ_name)`** — retrieve ingested domain knowledge about a specific civilisation from ChromaDB (unit strengths, typical build orders, common weaknesses)
- **`write_run_entry(run_data)`** — append the completed run record to `data/runs/` as JSONL
- **`write_coaching_report(report_text, run_id)`** — write the coaching report as a .txt file to `data/reports/`
- **`store_run_memory(summary)`** — embed and store the run summary in ChromaDB via `episodic.py`

---

## 8. Constraints

- Must not fabricate stats absent from the parser output. If a field is `null`, report it as unavailable — never estimate or infer a value and present it as parsed data.
- Must not modify the .aoe2record file or any file outside `data/` and `logs/`.
- Must not call any external API other than the Anthropic Claude API.
- Must not store personally identifiable information beyond the player name as it appears in the replay file.
- Must not run more than once concurrently on the same replay file.
- Use the PyPI release of `mgz` (`mgz` on PyPI). Do not pin to any fork unless a specific parser failure is confirmed and documented with a clear plan to migrate back when the official package is fixed.
- Civ resolution must use `mgz`'s own civ name string where available. A hardcoded `CIVS` dict may be kept as a last-resort fallback but must be clearly marked as such; any `civ_NN` result in output is a failure (see section 4).
- AI player detection relies on `user_id == 0xFFFFFFFF`; this sentinel must be documented and flagged in code so any future breakage is obvious.
- The historical context section must cover every human player in the game — it may not be omitted for any player, even if the result is "No previous games on record."
- The team synergy section must be present whenever two or more human players share a team; it may never be silently omitted. "No shared games on record" is a valid and complete team synergy section.

---

## 9. Data sources

| Source | Type | Purpose | Access level |
|---|---|---|---|
| `.aoe2record` replay files | File | Primary input; parsed each run | Read |
| ChromaDB (`data/chroma/`) | Vector database | Store and retrieve past run summaries, civ knowledge, reflection conclusions | Read-write |
| `data/runs/` | JSONL files | Append-only run history; source of truth for all past runs | Read-write |
| `data/reports/` | .txt files | Coaching reports, one per run | Write |
| `data/prompts/` | Files | Versioned prompt snapshots for `prompt_tuner.py` | Read-write |
| Anthropic Claude API | External API | Reasoning and coaching report generation | Write (outbound only) |

---

## 10. Improvement targets

- Increase coaching specificity over time: move from generic advice ("focus on villager production") toward player-specific patterns detected across multiple sessions ("you consistently lose games under 30 minutes — this may indicate a build order gap in the dark age").
- Improve civ knowledge depth: as more games are played with each civilisation, the agent should accumulate richer domain knowledge about how the player performs with that civ specifically.
- Improve team synergy analysis depth: as more shared games accumulate, move from simple win/loss record to pattern detection (e.g. "this pairing tends to lose when both players pick cavalry civs" or "your win rate together improves significantly in games over 40 minutes").
- Reduce reliance on generic fallback observations when data is limited: over time, reflection should identify which observations correlate with actual player improvement so lower-signal observations are weighted less.
- Track eAPM trend per player across sessions and surface it explicitly in the coaching report.
- Replace the rule-based evaluator with an LLM-as-judge variant: send the completed coaching report back to the Claude model with a structured scoring prompt keyed to the §3 success criteria; more nuanced than binary rule checks but adds latency and cost per run — defer until the rule-based baseline is stable.

---

## 11. Open questions

- Should the agent accept multiple replays in one run (e.g. a session of 3 games) and produce a combined session report, or always run once per file? Start with one file per run; revisit at v1.3.
- Should civ knowledge be seeded manually (ingested once from a known source) or built up organically from parsed game data? Decision pending — manual seed is safer for v1.1.
- What is the right eAPM benchmark to compare against? The parser provides raw eAPM but no Elo. Decide whether to hardcode a beginner/intermediate/advanced bracket, ask the user to self-report, or omit benchmarking entirely in v1.1 and rely on relative comparison to the player's own history instead.
- In multiplayer games with multiple human players, should `get_player_history` be called once per human player (potentially several tool calls per run), or should there be a batch variant? Decide before implementing `tools.py`.
- For team synergy, `get_team_history` matches on exact player combinations. Should it also return partial matches (e.g. Frank + Joris + a third player when only Frank + Joris are in the current game)? Partial matches add richness but complicate the query. Start with exact matches only.
- Should `parse_replay` attempt to use `mgz`'s own civilisation string directly (avoiding any hardcoded dict) or keep a dict as a verified fallback? Investigate what `mgz` actually returns for `p["civilization"]` before committing to either approach — this will also determine whether the dict from the previous agent can be dropped entirely.

---

## 12. Testing

**Test suite location:** `tests/`

**Required coverage:** Unit tests must exist for `core/parser.py`, `core/evaluator.py`, `core/database.py`, and `memory/retrieval.py`. Tests are run with `pytest`.

**Isolation requirement:** Tests that touch ChromaDB must use a temporary on-disk client (via pytest's `tmp_path` fixture) and must never read from or write to the production `data/chroma/` store.

**Pre-commit hook (required):** A git pre-commit hook must run `pytest tests/` before every commit. A commit that causes any test to fail must be blocked. The hook source is stored at `scripts/pre-commit` (tracked by git) and must be copied to `.git/hooks/pre-commit` and made executable once per clone (`cp scripts/pre-commit .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit`). This setup step is part of the installation instructions in `README.md`.

**Future improvement (v1.5):** A GitHub Actions workflow (`.github/workflows/test.yml`) will run the test suite automatically on every push (CI) and, if tests pass, SSH into the VPS to pull the latest code and restart the Docker stack (CD). This requires v1.4 (Docker + VPS) to be in place first, and the mgz fork dependency to be resolved before GitHub-hosted runners can install it cleanly.
