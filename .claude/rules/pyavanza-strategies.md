---
paths:
  - "src/services/ta/**"
  - "src/tasks/**"
---

# Strategy And Trading Loop

- `get_stored_strategies()` reads the strategy JSON schema: `rank`, `name`, `total_trades`, `total_profit`, `profitable_trades_share`. Keep `backtest.py` writing exactly that.
- When signal semantics or exit rules change, validate both `tasks/backtest.py` and `tasks/main.py`: they share indicator contracts but have different control flow.
- Bound strategy-combination growth in the backtest engine.
- Changing strategy-file naming, path logic, or ranking rules requires updating docs and deployment expectations in the same change.
