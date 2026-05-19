---
description: "Use when editing runtime entry points under src/task_*.py, src/development.py, or src/print_logs.sh. Covers delegation, logging setup, and operational safety."
applyTo:
  - "src/task_*.py"
  - "src/development.py"
  - "src/print_logs.sh"
---
# Entry Point Guidelines

- Keep entry scripts thin: set log handlers, call into `tasks/`, `apis/`, or `services/`, and handle top-level alerting or exception reporting only.
- `src/task_trade.py` is the live-trading entry point. Treat any change that could bypass `DRY_RUN`, change order placement timing, or alter exit behavior as high risk and validate narrowly.
- `src/task_end_of_day.py` and `src/task_end_of_week.py` mutate cached data and rewrite strategy ranking files; document any durable file-contract change.
- `src/development.py` is a manual experimentation surface; keep one-off tuning helpers there instead of leaking experimental code into production paths.
- `src/print_logs.sh` assumes the deployed Linux layout and GNU `date`; if you make it cross-platform or change log locations, update docs.