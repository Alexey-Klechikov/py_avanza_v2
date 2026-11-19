---
paths:
  - "src/services/ta/**"
  - "src/tasks/**"
  - "src/services/trading/**"
---

# Signal Source And Trading Loop

- Signal source: the weighted score (`tasks/shared/votes.py`, `weighted_model.py`; `tasks/shared/` holds what the live loop and the backtest share). `SETTINGS.LIVE_ORDERS` makes the live loop trade it (currently `False`); `False` only logs its signals as `[PAPER]`, and a failure there is only logged.
- `WeightedModel` (`config/<NAME>_weighted_model.json`) is read by the live loop and the paper replay and written by `train_weighted_model()`; keep its schema and file name in step with both readers.
- Signals act on closed bars only: a coarse bar votes from the 2m bar that completes it (`tasks/shared/coarse_bars.py`), daily votes use the previous session. Never let a backtest see a bar the live loop would not have. The live loop is the source of truth for timing: the backtest follows it (trading window by bar end, `tasks/shared/bars.py` `is_in_trading_window`), never the other way round.
- When signal semantics or exit rules change, validate the backtest (`tasks/backtest/simulator.py`, `paper_trade.py`) and the live loop (`tasks/trade/main.py`, `states.py`) together: they share signals (`services/ta/strategies/signals.py`, `Signal.from_bar`) and exit rules (`TrackedPosition`, `ExitLevels`: take-profit, stop loss, holding time) but have different control flow.
- Changing the model file name or path logic requires updating docs in the same change.
