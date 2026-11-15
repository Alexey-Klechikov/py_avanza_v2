---
paths:
  - "src/config/**"
---

# Configuration

- `settings.py` is the source of truth for trading defaults: instruments, trading window, risk controls, multiplier, indicator parameters.
- `SETTINGS_WATCHLIST` and `WatchlistNameComposition` encode the watchlist naming contract.
- `DRY_RUN` defaults from platform detection; document any change to that in `README.md` and `CLAUDE.md`.
- Never put manual notes into generated `OMX_trade_strategies*.json` files.
