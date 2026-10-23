---
paths:
  - "src/utils/**"
---

# Utilities

- Keep `src/utils/` small and repo-wide. Logging, constants, and formatting or filtering helpers belong here; strategy logic and API workflows do not.
- Preserve the logger's dual local and deployed path handling in `src/utils/logger/operators.py`. Local runs write under `src/logs/`; deployed runs write under `logs/`.
- If you change log naming, handler setup, or logger hierarchy, update `CLAUDE.md` and any operational scripts that tail logs.
