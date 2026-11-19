---
paths:
  - "src/config/**"
---

# Configuration

- `settings.py` is the source of truth for trading defaults: instruments, trading window, risk controls, multiplier, indicator parameters.
- `SETTINGS_WATCHLIST` and `WatchlistNameComposition` encode the watchlist naming contract.
- `DRY_RUN` defaults from platform detection; document any change to that in `README.md` and `CLAUDE.md`.
- `<NAME>_weighted_model.json` (`TSLA_weighted_model.json`) is generated; hand-edit only its weights, and never add fields the `WeightedModel` schema rejects.
