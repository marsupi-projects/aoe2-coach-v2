---
name: next-session-priority
description: First thing to address next session — data/ gitignore decision for knowledge files
metadata: 
  node_type: memory
  type: project
  originSessionId: 983c2a0e-4b41-4f4c-98b4-4555b145d7ae
---

Start next session by explaining why `data/` is fully gitignored, then decide whether `data/knowledge/` should be an exception.

**Why:** The four civ JSON files (`britons.json`, `persians.json`, `khmer.json`, `byzantines.json`) and `_template.json` live in `data/knowledge/civs/` which is gitignored. They are currently not version-controlled and won't reach the VPS on deploy.

**The tension to explain:** `data/` is ignored because it contains runtime-generated files (ChromaDB store, run history, coaching reports, replays) that are large, environment-specific, or sensitive. But `data/knowledge/` is different — it's human-authored source material that belongs in version control, not generated output.

**The decision:** Either add a `.gitignore` exception for `data/knowledge/` (track it like source code) or move `data/knowledge/` outside `data/` entirely (e.g. `knowledge/`). Make this choice before committing the session 08 work.

**How to apply:** Do not let the user commit the session 08 work without resolving this first — the civ files are stranded outside git until it's resolved.
