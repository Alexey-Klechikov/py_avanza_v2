---
paths:
  - "src/apis/**"
---

# API Integrations

- Operators own repo-facing workflows: watchlist refresh, portfolio filtering, order lifecycle, transaction summaries.
- `client.py` loads credentials from `config/.env` on the host and `src/config/.env` locally; keep both because deploy flattens `src/` into the remote root.
- `src/apis/telegram/` wraps `telegram-send` and reads no repo bot token.
- Avanza order, watchlist, portfolio, and transaction flows can hit a live account; prefer model tests or dry-run-safe paths over running integration code. Keep retry bounds on every broker call.
