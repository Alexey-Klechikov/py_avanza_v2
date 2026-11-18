---
paths:
  - "src/services/ta/**"
  - "src/tasks/**"
  - "src/services/trading/**"
---

# Signal Sources And Trading Loop

- Signal sources (`SignalSource` in `tasks/trade/models.py`): the fixed rule (`tasks/fixed_rule.py`) and the weighted score (`tasks/backtest/votes.py`, `model.py`). `SETTINGS.LIVE_SIGNAL_SOURCE` picks the live one; `None` (default) places no orders. Keep a paper source's failure from reaching the live one.
- `WeightedModel` (`config/OMX_weighted_model.json`) is read by the live loop and the paper replay and written by `train_weighted_model()`; keep its schema and file name in step with both readers.
- Signals act on closed bars only: a coarse bar votes or signals from the 2m bar that completes it (`tasks/coarse_bars.py`), daily votes use the previous session. Never let a backtest see a bar the live loop would not have.
- When signal semantics or exit rules change, validate the backtest (`tasks/backtest/simulator.py`, `paper_trade.py`) and the live loop (`tasks/trade/main.py`, `states.py`) together: they share signals (`services/ta/strategies/signals.py`, `Signal.from_bar`) and exit rules (`TrackedPosition`, `ExitLevels`: take-profit, stop loss, pullback, holding time) but have different control flow.
- Changing the model file name, path logic, or a source's frozen parameters (`FIXED_RULE`) requires updating docs in the same change; a changed fixed rule restarts its paper test.
