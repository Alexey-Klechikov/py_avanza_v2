# pyAvanza_v2

Python 3.13 trading bot: caches OHLCV data, builds and ranks TA strategies, runs a live Avanza loop that can place real orders. Overview, runtime, and deploy flow: [README.md](README.md).

## Setup
- `uv sync` (interpreter pinned in `.python-version`, repo-local `.venv`). Create `src/data/` first: `Storage.write()` in `src/services/storage/operators.py` does not create it.
- Credentials (`AVA_USERNAME`, `AVA_PASS`, `AVA_TOTP`): `src/config/.env` locally, `config/.env` on the host (written by the deploy workflow from GitHub Secrets).

## Map
- [src/task_trade.py](src/task_trade.py) live entry → [src/tasks/main.py](src/tasks/main.py) loop (cached data, top strategies, signals → `FlowAction`, flow control) → `src/apis/avanza/trade/operator.py`. Signal translation: `src/tasks/models.py`.
- [src/tasks/backtest.py](src/tasks/backtest.py): simulated trades and ranked strategy generation.
- [src/task_end_of_day.py](src/task_end_of_day.py), [src/task_end_of_week.py](src/task_end_of_week.py): cache and strategy refresh.
- `src/apis/{avanza,yahoo,telegram}/`: `client/` adapts payloads and retries (shapes in `client/models/`; Avanza auth in `src/apis/avanza/client/client.py`); `operators/` holds repo workflows (`watchlists.py`, `orders.py`, `portfolio.py`, `transactions.py`).
- `src/services/ta/`: indicators, plotting, strategy composition, JSON persistence (`operators.py`, `strategies/operators.py`). `services/storage/`: OHLCV cache. `services/calendar/`: Stockholm market hours.
- [src/config/settings.py](src/config/settings.py): trading window, risk controls, multiplier, indicator parameters. `src/utils/`: logging, constants.
- [.github/workflows/deploy.yaml](.github/workflows/deploy.yaml): remote layout and cron (the only file under `.github/`). `.claude/`: agents, path-scoped rules, skills, pre-push hooks.

## Conventions
- `src/task_*.py` and `src/development.py` stay thin: set handlers, call operators/tasks, own top-level exception and alert handling.
- `src/apis/*/client/` only adapts third-party payloads and retries; repo-specific workflows live in `src/apis/*/operators/`; strategy scoring and TA never live in `apis/`.
- `services/ta/**` has no broker/account side effects; live trading stays in `tasks/main.py` and `apis/avanza/trade/operator.py`.
- Imports use the flat roots under `src/` (`apis`, `config`, `services`, `tasks`, `utils`), never `src.`; `src/` is the path root for scripts and pytest (`pythonpath = ["src"]`). Keep `__init__.py` files empty, no barrel re-exports.
- Dual paths: local `src/config`, `src/data`, `src/logs`; host `config`, `data`, `logs` (deploy syncs only the contents of `src/` to `/home/ubuntu/pyAvanza/`). Preserve both.
- `src/config/OMX_trade_strategies*.json` are generated; the live loop reads them by name. Preserve schema and naming.
- Watchlist names are `DT_<direction>_<instrument>_<instrument_type>`; change `WatchlistNameComposition` and the operators together.
- Alerts call `telegram-send` directly (machine-level config, fails at send time; no setting in `settings.py`).
- Python style, nesting, and complexity: `.claude/rules/pyavanza-python.md`.

## Validation
- Fast check: `uv run python -m compileall src .claude/hooks`. Focused: `uv run pytest <path>`. Suite: `uv run pytest`. Dependencies: `uv lock`.
- Credential-free unit tests: `src/apis/avanza/client/models/**`, `src/apis/yahoo/client/models/history_request_test.py`. `src/apis/avanza/client/client_test.py` is integration coverage that needs `src/config/.env` and can hit the live account.
- Never run `src/task_trade.py` to validate: `TradeStrategies.DRY_RUN` is `False` outside Darwin, so it can place live orders. `task_end_of_day.py` rewrites cached data and strategy files; `task_end_of_week.py` regenerates the dev strategy snapshots (`dev_<INDICATORS_START>` … `dev_<INDICATORS>`). An empty final test writes an empty live strategies file (no trading) and alerts.

## Pitfalls
- Cron starts the live loop once; it runs until shortly after `SETTINGS.TIME.END` (cron does not invoke it every two minutes).
- [src/print_logs.sh](src/print_logs.sh) assumes the Linux host layout and GNU `date -d`.
- Logs and `daily_trading_stats_OMX.json` accumulate under `src/logs/` locally, `logs/` on the host.

## Docs And Automation
- Update `README.md` and `CLAUDE.md` with changes to `src/apis/avanza/client/client.py`, `src/config/settings.py`, `src/services/storage/operators.py`, `src/services/ta/strategies/operators.py`, `src/task_*.py`, or `deploy.yaml`; update `CLAUDE.md` with changes to `pyproject.toml`, `.pre-commit-config.yaml`, or `.claude/{hooks,agents,skills,rules}/`.
- `git push` runs two blocking gates: `documentation-alignment` (`documenter` fixes stale docs, blocks if it edited) and `code-review` (`code-reviewer`, blocks on blocking findings). Pre-check with `python3 .claude/hooks/pre_push_documentation.py --working-tree` or `pre_push_code_review.py --working-tree`; bypass once with `SKIP=<gate-id> git push`. A blocked gate prints a paste-ready Claude prompt that fixes everything, self-checks both gates, and commits; passes are recorded in `.git/claude-gates/`, so pushing identical content skips review. Details: `.claude/rules/claude-customizations.md`.
- Agents: `code-reviewer` before a deploy or PR, `documenter` for doc drift, `refactorer` only for a requested behavior-preserving cleanup. `/code-review-skill` and `/documentation-skill` run the first two in a forked context. Do not reintroduce `AGENTS.md` or Copilot customizations.
