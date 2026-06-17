---
name: next-session-priority
description: "Deploy agent to VPS — install Docker, clone repo, run stack"
metadata: 
  node_type: memory
  type: project
  originSessionId: 983c2a0e-4b41-4f4c-98b4-4555b145d7ae
---

v1.4 Docker is complete and tested locally. Next step is getting the stack running on the VPS before tackling v1.5 CI/CD.

**User's VPS:** Already provisioned and security hardened. Docker is NOT installed yet.

**Next session order:**
1. SSH into the VPS
2. Install Docker (guide the user through this — they are not familiar with Docker)
3. Clone the repo
4. Create `.env` on the server
5. `docker compose up -d`
6. Test a run on the VPS

Once the stack runs manually on the VPS, v1.5 CI/CD (GitHub Actions auto-deploy on push) can be added on top.

**How to apply:** Do not skip straight to CI/CD — manual deploy first, then automate it.
