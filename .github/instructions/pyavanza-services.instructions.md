---
description: "Use when editing storage or market-calendar helpers under src/services/storage/ or src/services/calendar/. Covers persistence and market-hours boundaries."
applyTo:
  - "src/services/storage/**"
  - "src/services/calendar/**"
---
# Runtime Services Guidelines

- Keep `src/services/storage/` limited to local cache persistence for OHLCV data. The current contract is pickle-backed pandas DataFrames keyed by symbol and resolution.
- Keep `src/services/calendar/` limited to market-session calculations. Trading-window policy still lives in `src/config/settings.py` and the live loop.
- Local runs resolve artifact paths under `src/data/`; the deployed host resolves them under `data/` because `.github/workflows/deploy.yaml` syncs `src/` into the server root. Preserve that dual-mode behavior unless you change deployment too.
- `Storage.write()` assumes the target `data/` directory already exists. If you change that assumption or path layout, update `README.md` and `AGENTS.md`.