---
description: "Use when editing the deploy workflow under .github/workflows/deploy.yaml. Covers the remote layout, preserved directories, and cron contract."
applyTo: ".github/workflows/deploy.yaml"
---
# Deploy Workflow Guidelines

- The workflow deploys only the contents of `src/` to `/home/ubuntu/pyAvanza/`; root-level repo files are not synced to the host.
- Preserve the remote `data`, `logs`, `config`, and `.venv` directories. They hold persistent state, generated artifacts, secrets, and the runtime environment.
- The cron job starts `task_trade.py` once per trading day and relies on the script's internal loop to run until the end of the session. Do not convert it into a high-frequency cron invocation unless you change the runtime model deliberately.
- If remote layout, credential provisioning, or cron scheduling changes, update `README.md` and `AGENTS.md` in the same change.