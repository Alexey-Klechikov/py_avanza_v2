---
paths:
  - "src/services/storage/**"
  - "src/services/calendar/**"
  - "src/utils/**"
---

# Runtime Services And Utilities

- `services/storage/` is local OHLCV cache only: pickle-backed pandas DataFrames keyed by symbol and resolution.
- `services/calendar/` is market-session math only; trading-window policy stays in `config/settings.py` and the live loop.
- `src/utils/` stays small and repo-wide (logging, constants, formatting/filter helpers, retry backoff); no strategy logic or API workflows.
- `utils/logger/operators.py` keeps the dual local/host log paths; log naming or handler changes must also update docs and scripts that tail logs.
