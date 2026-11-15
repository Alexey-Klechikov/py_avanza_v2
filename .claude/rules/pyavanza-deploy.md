---
paths:
  - ".github/workflows/deploy.yaml"
---

# Deploy Workflow

- Preserve the remote `data`, `logs`, `config`, and `.venv` directories: persistent state, generated artifacts, secrets, legacy virtualenv (kept for rollback).
- Cron entries call `REMOTE_PYTHON` (`/usr/bin/python3.13`); keep the pre-check that fails the deploy before touching cron when it is missing.
- Cron starts `task_trade.py` once per trading day; keep it that way unless the runtime model changes deliberately.
