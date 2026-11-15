---
paths:
  - "src/task_*.py"
  - "src/development.py"
  - "src/print_logs.sh"
---

# Entry Points

- Any change in `task_trade.py` that could bypass `DRY_RUN`, shift order timing, or alter exits is high risk; validate narrowly.
- `print_logs.sh` assumes the host layout and GNU `date`; update docs if it becomes cross-platform or log locations change.
- `development.py` is the manual experimentation surface; keep one-off tuning helpers there, out of production paths.
