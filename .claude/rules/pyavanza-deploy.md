---
paths:
  - ".github/workflows/deploy.yaml"
---

# Deploy Workflow

- The workflow deploys only the contents of `src/` to `/home/ubuntu/pyAvanza/`; root-level repo files are not synced to the host.
- Preserve the remote `data`, `logs`, `config`, and `.venv` directories. They hold persistent state, generated artifacts, secrets, and the runtime environment.
- The cron job starts `task_trade.py` once per trading day and relies on the script's internal loop to run until the end of the session. Do not convert it into a high-frequency cron invocation unless you change the runtime model deliberately.
- If remote layout, credential provisioning, or cron scheduling changes, update `README.md` and `CLAUDE.md` in the same change.
