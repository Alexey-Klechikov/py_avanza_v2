---
description: "Use when editing runtime settings, credential files, or generated strategy snapshots under src/config/. Defines what belongs in dataclass settings versus generated JSON."
applyTo: "src/config/**"
---
# Configuration Guidelines

- Keep `src/config/settings.py` as the source of truth for trading defaults: instrument selection, trading window, risk controls, multiplier, and indicator parameters belong there.
- `src/config/.env` is the local credential surface for `AVA_USERNAME`, `AVA_PASS`, and `AVA_TOTP`. The deploy workflow writes the remote `config/.env` file from GitHub Secrets.
- `OMX_trade_strategies*.json` files are generated artifacts consumed by live trading and backtests. Preserve their schema and naming conventions; do not mix manual notes into those files.
- `SETTINGS_WATCHLIST` and `WatchlistNameComposition` expect names like `DT_<direction>_<instrument>_<instrument_type>`. If you change the naming contract, update the watchlist operators and docs together.
- `DRY_RUN` currently defaults from platform detection. If that behavior changes, document it in both `README.md` and `AGENTS.md`.