---
description: "Use when editing broker, market-data, or alert integrations under src/apis/. Defines client/operator/model boundaries, credential loading, and live-account safety."
applyTo: "src/apis/**"
---
# API Integration Guidelines

- Keep `src/apis/*/client/` for adapting third-party payloads, retries, and low-level request handling. Keep parsed shapes in `client/models/`.
- Keep `src/apis/*/operators/` for repo-facing workflows such as watchlist refresh, portfolio filtering, order lifecycle, and transaction summaries. Do not move strategy scoring or TA logic into this layer.
- Preserve the current credential contract in `src/apis/avanza/client/client.py`: credentials are loaded from `config/.env` on the deployed host and from `src/config/.env` during local runs because the deploy workflow flattens `src/` into the remote root.
- `src/apis/telegram/` uses `telegram-send`; it does not read a repo-specific bot token. If alert delivery changes, update `README.md` and `AGENTS.md`.
- Avanza order, watchlist, portfolio, and transaction flows can hit a live account. Prefer model tests or dry-run-safe paths before running integration code.