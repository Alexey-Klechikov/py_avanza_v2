---
description: "Use when editing technical indicators, strategy ranking, backtesting, or live signal orchestration under src/services/ta/ and src/tasks/trade_strategies/."
applyTo:
  - "src/services/ta/**"
  - "src/tasks/trade_strategies/**"
---
# Strategy and Trading Loop Guidelines

- Keep `src/services/ta/**` focused on indicator calculation, plotting, strategy composition, and strategy-file persistence. Do not add broker calls or account-side effects there.
- Keep `src/tasks/trade_strategies/backtest.py` responsible for simulated order logic and ranked-strategy generation. Preserve the JSON schema consumed by `get_stored_strategies()`: `rank`, `name`, `total_trades`, `total_profit`, and `profitable_trades_share`.
- Keep `src/tasks/trade_strategies/main.py` responsible for the live decision loop: loading cached data, selecting top strategies, translating signals into `FlowAction`, and coordinating the `Trade` operator.
- Strategy files are named `src/config/OMX_trade_strategies*.json` locally and `config/OMX_trade_strategies*.json` on the deployed host. If you change naming, path logic, or ranking rules, update docs and deployment expectations in the same change.
- When changing signal semantics or exit rules, validate both the backtest path and the live loop path. They share indicator contracts but implement different control flow.