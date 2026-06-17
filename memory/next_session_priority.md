---
name: next-session-priority
description: v1.4 complete — next is v1.5 CI/CD (GitHub Actions + VPS deploy)
metadata: 
  node_type: memory
  type: project
  originSessionId: 983c2a0e-4b41-4f4c-98b4-4555b145d7ae
---

v1.4 Docker is complete and tested. Next milestone is v1.5 CI/CD:
- GitHub Actions runs test suite on every push
- If tests pass, workflow SSHs into VPS, pulls latest code, restarts Docker stack

**Prerequisite:** A VPS needs to be provisioned first. User does not have one yet. Start next session by discussing VPS options before writing any CI/CD config.

**How to apply:** Do not jump straight into GitHub Actions config — the SSH deploy step requires a VPS IP, credentials, and Docker installed on the server. Establish that first.
