# pyAvanza_v2

## Fast Start
- Use Python 3.13 with `uv`. The repo pins the interpreter in `.python-version` and uses a repo-local `.venv`.
- Install dependencies with `uv sync`.
- Create `src/data/` locally before running cache or trading flows; `Storage.write()` assumes that directory already exists.
- Put Avanza credentials in `src/config/.env` for local runs. The deployed host uses `config/.env`.
- Prefer `uv run python -m compileall src .claude/hooks` as the quickest repo-wide sanity check after edits.

## Where To Look First
- [README.md](README.md) for the project overview, runtime expectations, and deploy flow.
- [src/task_trade.py](src/task_trade.py) for the live trading entry point.
- [src/tasks/main.py](src/tasks/main.py) for the trading loop, signal evaluation, and flow control.
- [src/tasks/backtest.py](src/tasks/backtest.py) for simulated trades and ranked strategy generation.
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
- `src/tasks/**`: live trading flow (`main.py`), signal translation (`models.py`), and the backtest engine (`backtest.py`).
- `src/config/**`: code-backed settings, local credentials, and generated `OMX_trade_strategies*.json` files.
- `src/utils/**`: logging and small shared constants.
- `.github/**`: the deploy workflow only.
- `.claude/**`: Claude Code agents, path-scoped rules, and pre-push review hooks.

## Codebase Conventions
- Keep `src/task_*.py` and `src/development.py` thin. They should set handlers, call into operators/tasks, and own top-level exception or alert handling only.
- Keep `src/apis/*/client/` for third-party payload adaptation and retries; keep repo-specific workflows in `src/apis/*/operators/`.
- Keep `src/services/ta/**` free of broker/account side effects. Live trading stays in `src/tasks/main.py` and `src/apis/avanza/trade/operator.py`.
- Strategy ranking files under `src/config/OMX_trade_strategies*.json` are generated artifacts. Preserve their schema and naming because the live loop reads them by convention.
- Path handling is intentionally dual-mode. Local runs read and write under `src/config`, `src/data`, and `src/logs`, while the deployed server uses `config`, `data`, and `logs` after [.github/workflows/deploy.yaml](.github/workflows/deploy.yaml) syncs `src/` into the remote root.
- Watchlists are parsed by name in the format `DT_<direction>_<instrument>_<instrument_type>`. If you change the prefix or part count, update `WatchlistNameComposition` and the surrounding operator logic together.
- `telegram-send` is used directly for alerts. There is no repo-specific Telegram setting in `src/config/settings.py`.
- Imports are flat package roots under `src/` (`apis`, `config`, `services`, `tasks`, `utils`), never prefixed with `src.`. `src/` itself is the path root, both when running `uv run python src/task_trade.py` and via pytest's `pythonpath = ["src"]`. Keep `__init__.py` files empty; do not add barrel re-export lists.

## Validation Notes
- Cheapest executable check: `uv run python -m compileall src .claude/hooks`.
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
- `git push` runs two blocking gates through `.pre-commit-config.yaml` (see `.claude/rules/claude-customizations.md`): `documentation-alignment` ([.claude/hooks/pre_push_documentation.py](.claude/hooks/pre_push_documentation.py)) has the `documenter` agent fix stale docs and blocks if it edited anything, and `code-review` ([.claude/hooks/pre_push_code_review.py](.claude/hooks/pre_push_code_review.py)) has the `code-reviewer` agent review the pushed code and blocks on blocking findings.
- Run either gate with `--working-tree` to check upstream..working tree before committing. Bypass one push with `SKIP=documentation-alignment git push` or `SKIP=code-review git push`.
- The code-review gate skips Markdown, `uv.lock`, and generated strategy snapshots. If a generated-artifact schema or path contract changes, update the relevant docs anyway.

## Claude Code Customizations
- `CLAUDE.md` (this file) is the single contributor baseline. `AGENTS.md` and the Copilot `.github` customizations were removed; do not reintroduce them. When a durable runtime, contributor, or workflow fact changes, update this file.
- `.claude/agents/` holds three agents: `documenter` (verified documentation updates), `code-reviewer` (read-only review for correctness, security, live-account safety, and conventions), and `refactorer` (behavior-preserving cleanups across `src/**`). The first two also back the pre-push gates. There are no skills.
- `.claude/rules/*.md` hold path-scoped guidance keyed by frontmatter `paths` globs. Keep each rule narrowly scoped and avoid duplicating one rule across multiple files; see `.claude/rules/claude-customizations.md` for the full policy on agents, hooks, and the pre-push gates.
- Use `documenter` for CLAUDE.md/README.md audits or after workflow and runtime changes. Use `code-reviewer` before a production deploy or pull request. Use `refactorer` only for a requested, evidence-backed behavior-preserving cleanup.
