# pyAvanza_v2

## Fast Start
- Use Python 3.13 with `uv`. The repo pins the interpreter in `.python-version` and uses a repo-local `.venv`.
- Install dependencies with `uv sync`.
- Create `src/data/` locally before running cache or trading flows; `Storage.write()` assumes that directory already exists.
- Put Avanza credentials in `src/config/.env` for local runs. The deployed host uses `config/.env`.
- Prefer `uv run python -m compileall src .github/hooks/scripts` as the quickest repo-wide sanity check after edits.

## Where To Look First
- [README.md](README.md) for the project overview, runtime expectations, and deploy flow.
- [src/task_trade.py](src/task_trade.py) for the live trading entry point.
- [src/tasks/trade_strategies/main.py](src/tasks/trade_strategies/main.py) for the trading loop, signal evaluation, and flow control.
- [src/tasks/trade_strategies/backtest.py](src/tasks/trade_strategies/backtest.py) for simulated trades and ranked strategy generation.
- [src/task_end_of_day.py](src/task_end_of_day.py) and [src/task_end_of_week.py](src/task_end_of_week.py) for scheduled cache and strategy-refresh workflows.
- [src/apis/avanza/client/client.py](src/apis/avanza/client/client.py) for Avanza authentication, retries, and typed API wrappers.
- [src/apis/avanza/operators/watchlists.py](src/apis/avanza/operators/watchlists.py), [src/apis/avanza/operators/orders.py](src/apis/avanza/operators/orders.py), [src/apis/avanza/operators/portfolio.py](src/apis/avanza/operators/portfolio.py), and [src/apis/avanza/operators/transactions.py](src/apis/avanza/operators/transactions.py) for live account workflows.
- [src/services/ta/operators.py](src/services/ta/operators.py) and [src/services/ta/strategies/operators.py](src/services/ta/strategies/operators.py) for indicator wiring and strategy-file persistence.
- [src/config/settings.py](src/config/settings.py) for trading window, risk controls, multiplier, and indicator parameters.
- [.github/workflows/deploy.yaml](.github/workflows/deploy.yaml) for the remote layout and cron contract.

## Project Shape
- `src/apis/**`: Avanza, Yahoo Finance, and Telegram integrations plus repo-facing operators.
- `src/services/ta/**`: indicator computation, plotting, strategy composition, and JSON strategy persistence.
- `src/services/storage/**` and `src/services/calendar/**`: OHLCV cache persistence and Stockholm market-hours helpers.
- `src/tasks/trade_strategies/**`: live trading flow, signal translation, and backtest engine.
- `src/config/**`: code-backed settings, local credentials, and generated `OMX_trade_strategies*.json` files.
- `src/utils/**`: logging and small shared constants.
- `.github/**`: deploy workflow plus Copilot agents, instructions, and documentation reminders.

## Codebase Conventions
- Keep `src/task_*.py` and `src/development.py` thin. They should set handlers, call into operators/tasks, and own top-level exception or alert handling only.
- Keep `src/apis/*/client/` for third-party payload adaptation and retries; keep repo-specific workflows in `src/apis/*/operators/`.
- Keep `src/services/ta/**` free of broker/account side effects. Live trading stays in `src/tasks/trade_strategies/main.py` and `src/apis/avanza/trade/operator.py`.
- Strategy ranking files under `src/config/OMX_trade_strategies*.json` are generated artifacts. Preserve their schema and naming because the live loop reads them by convention.
- Path handling is intentionally dual-mode. Local runs read and write under `src/config`, `src/data`, and `src/logs`, while the deployed server uses `config`, `data`, and `logs` after [.github/workflows/deploy.yaml](.github/workflows/deploy.yaml) syncs `src/` into the remote root.
- Watchlists are parsed by name in the format `DT_<direction>_<instrument>_<instrument_type>`. If you change the prefix or part count, update `WatchlistNameComposition` and the surrounding operator logic together.
- `telegram-send` is used directly for alerts. There is no repo-specific Telegram setting in `src/config/settings.py`.

## Validation Notes
- Cheapest executable check: `uv run python -m compileall src .github/hooks/scripts`.
- Cheapest unit tests: the model tests under `src/apis/avanza/client/models/**` and `src/apis/yahoo/client/models/history_request_test.py`.
- `src/apis/avanza/client/client_test.py` is integration coverage. It requires valid credentials in `src/config/.env` and can hit a live Avanza account.
- `uv run python src/task_end_of_day.py` rewrites cached data and strategy files.
- `uv run python src/task_end_of_week.py` regenerates the dev strategy snapshots in `src/config/`.
- Be cautious with `uv run python src/task_trade.py` on non-macOS hosts. `TradeStrategies.DRY_RUN` defaults to `False` outside Darwin, so the script can place live orders.

## Common Pitfalls
- `src/services/storage/operators.py` does not create the `data/` directory. Fresh local checkouts need `src/data/` before cache, backtest, or trade flows can write data.
- The deploy workflow copies only the contents of `src/` to `/home/ubuntu/pyAvanza/`; root-level repo files are not synced to the host.
- [src/print_logs.sh](src/print_logs.sh) assumes the deployed Linux layout and GNU `date -d`, so it is not a portable local helper on macOS.
- Logs accumulate under `src/logs/` locally and `logs/` on the server. `daily_trading_stats_OMX.json` is written there too.
- The live loop starts once from cron and then keeps running until shortly after `SETTINGS.TIME.END`; the cron job is not responsible for invoking it every two minutes.
- Alert delivery depends on machine-level `telegram-send` configuration. Missing local Telegram setup will fail at send time, not at import time.

## Automation Notes
- [.github/workflows/deploy.yaml](.github/workflows/deploy.yaml) writes `config/.env` on the remote host from GitHub Secrets and refreshes the project cron section.
- [check_documentation_alignment.py](.github/hooks/scripts/check_documentation_alignment.py) is the deterministic documentation-routing check. Run `python3 .github/hooks/scripts/check_documentation_alignment.py` from the repository root before completing changes that affect durable workflow or runtime contracts.
- The checker requires `AGENTS.md` for changes to `pyproject.toml` or Copilot customization files. It requires both `AGENTS.md` and `README.md` for deploy changes and the explicit runtime-contract owners: settings, Avanza credential loading, storage, strategy persistence, and scheduled task entry points.
- Generated cache, log, and strategy snapshot updates intentionally do not trigger the checker. If a generated-artifact schema or path contract changes, update the relevant docs anyway.
- A Stop hook runs the same checker as a backstop. Hooks cannot run skills. When it blocks completion, load and execute `documentation-skill`, make the evidence-backed documentation updates, then rerun the checker.

## Copilot Customizations
- `AGENTS.md` is the concise contributor baseline. [.github/copilot-instructions.md](.github/copilot-instructions.md) contains repo-wide engineering behavior; path-specific rules belong in [.github/instructions/](.github/instructions/).
- [.github/agents/linus.agent.md](.github/agents/linus.agent.md) is the primary implementation agent. It coordinates focused validation and the documentation checker; do not duplicate specialized workflows in the agent.
- Use `documentation-skill` for documentation audits, instruction/hook updates, or any checker-routed pass. Use `code-review-skill` before a production deploy or pull request. Use `refactoring-skill` only for a requested, evidence-backed behavior-preserving cleanup.
- Follow [documentation-scope.instructions.md](.github/instructions/documentation-scope.instructions.md) to route durable facts between `AGENTS.md` and `README.md`. Keep skills reusable and on-demand, instructions narrowly scoped with `applyTo`, and hooks fast and deterministic.
