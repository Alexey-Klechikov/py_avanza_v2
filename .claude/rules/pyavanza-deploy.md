---
paths:
  - ".github/workflows/deploy.yaml"
---

# Deploy Workflow

- Preserve the remote `data`, `logs`, `config`, and `.venv` directories: persistent state, generated artifacts, secrets, runtime environment.
- Cron starts `task_trade.py` once per trading day; keep it that way unless the runtime model changes deliberately.
