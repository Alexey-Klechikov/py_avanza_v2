---
paths:
  - "src/services/ta/**"
  - "src/tasks/**"
  - "src/services/trading/**"
---

# Strategy And Trading Loop

- `get_stored_strategies()` reads the strategy JSON schema: `rank`, `name`, `total_trades`, `total_profit`, `profitable_trades_share`. Keep `dump_strategies_in_file()` (called by `tasks/backtest/runner.py`) writing exactly that. The live loop orders and gives priority to strategies by stored `rank` (1 is best), the order the final test writes them in (`select_daily_strategies()` expected edge for `OMX_trade_strategies.json`; `select_training_strategies()` for the `dev_*` snapshots).
- When signal semantics or exit rules change, validate both `tasks/backtest/` and `tasks/main.py` with `tasks/trade.py`: they share indicator contracts, strategy signals (`services/ta/strategies/signals.py`, `Signal.from_bar`), and `services/trading/` (the rank lock in `StrategyTrigger`, exit levels in `TrackedPosition`), but have different control flow.
- Bound strategy-combination growth in the backtest engine.
- Changing strategy-file naming, path logic, or ranking rules requires updating docs and deployment expectations in the same change.
