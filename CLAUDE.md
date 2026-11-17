# pyAvanza_v2

Python 3.13 trading bot: caches OHLCV data, builds and ranks TA strategies, runs a live Avanza loop that can place real orders. Overview, runtime, and deploy flow: [README.md](README.md).

## Setup
- `uv sync` (interpreter pinned in `.python-version`, repo-local `.venv`). Create `src/data/` first: `Storage.write()` in `src/services/storage/operators.py` does not create it.
- Credentials (`AVA_USERNAME`, `AVA_PASS`, `AVA_TOTP`): `src/config/.env` locally, `config/.env` on the host (written by the deploy workflow from GitHub Secrets).

## Map
- [src/task_trade.py](src/task_trade.py) live entry → [src/tasks/main.py](src/tasks/main.py) loop (cached data, top strategies, signals → `FlowAction`, flow control) → `src/tasks/trade.py` (live orders, exit levels). `Direction`, `FlowAction`: `src/tasks/models.py`.
- `src/tasks/backtest/`: backtest engine; [runner.py](src/tasks/backtest/runner.py) runs one step (simulate, select, write the strategies file) with `simulator.py`, `live_replay.py`, `scoring.py`, `selection.py`, `walk_forward.py`.
- [src/task_end_of_day.py](src/task_end_of_day.py), [src/task_end_of_week.py](src/task_end_of_week.py): cache and strategy refresh.
- `src/apis/{avanza,yahoo,telegram}/`: `client/` adapts payloads and retries (shapes in `client/models/`; Avanza auth in `src/apis/avanza/client/client.py`); `operators/` holds repo workflows (`watchlists.py`, `orders.py`, `portfolio.py`, `transactions.py`).
- `src/services/ta/`: indicators, plotting, strategies (`Strategy`, `TradeStats`, `Signal`, signal marking in `strategies/signals.py`), composition and JSON persistence (`operators.py`, `strategies/operators.py`). `services/trading/`: trading rules shared by backtest and live loop (`StrategyTrigger` rank lock, `TrackedPosition` exit levels). `services/storage/`: OHLCV cache (a new fetch replaces the stored candle with the same timestamp), `windows.py` (`DataWindow`, `CalibrationWindows`). `services/calendar/`: Stockholm market hours.
- [src/config/settings.py](src/config/settings.py): trading window, risk controls, multiplier, backtest spread, calibration windows, selection scoring, indicator parameters. `src/utils/`: logging, constants.
- [.github/workflows/deploy.yaml](.github/workflows/deploy.yaml): remote layout and cron (the only file under `.github/`). `.claude/`: agents, path-scoped rules, skills, pre-push hooks.

## Conventions
- `src/task_*.py` and `src/development.py` stay thin: set handlers, call operators/tasks, own top-level exception and alert handling.
- Layers: each `apis/<name>` and each `services/<name>` is isolated and imports only itself, `config`, and `utils` (never another `apis/*` or `services/*` branch, nor `tasks`); `config`/`utils` import no layer; `tasks/`, `task_*.py`, and `development.py` compose everything. `tests/test_architecture.py` enforces this.
- `src/apis/*/client/` only adapts third-party payloads and retries; repo-specific workflows live in `src/apis/*/operators/`; strategy scoring and TA never live in `apis/`.
- `services/**` has no broker/account side effects; live trading stays in `tasks/main.py` and `tasks/trade.py`.
- Imports use the flat roots under `src/` (`apis`, `config`, `services`, `tasks`, `utils`), never `src.`; `src/` is the path root for scripts and pytest (`pythonpath = ["src"]`). Keep `__init__.py` files empty, no barrel re-exports.
- Dual paths: local `src/config`, `src/data`, `src/logs`; host `config`, `data`, `logs` (deploy syncs only the contents of `src/` to `/home/ubuntu/pyAvanza/`). Preserve both.
- `src/config/OMX_trade_strategies*.json` are generated; the live loop reads them by name. Preserve schema and naming.
- Watchlist names are `DT_<direction>_<instrument>_<instrument_type>`; change `WatchlistNameComposition` and the operators together.
- Alerts call `telegram-send` directly (machine-level config, fails at send time; no setting in `settings.py`).
- Python style, nesting, and complexity: `.claude/rules/pyavanza-python.md`.

## Validation
- Fast check: `uv run python -m compileall src .claude/hooks`. Focused: `uv run pytest <path>`. Suite: `uv run pytest`. Dependencies: `uv lock`.
- Tests live in `tests/`, mirroring `src/` (`tests/<package>/test_<module>.py`); pytest uses `testpaths = ["tests"]`, `--import-mode=importlib`, and skips `integration` tests unless run with `-m integration`. Everything except `tests/apis/avanza/client/test_client.py` is credential-free; that file is integration coverage that needs `src/config/.env` and can hit the live account.
- Never run `src/task_trade.py` to validate: `DRY_RUN` is `False` outside Darwin, so it can place live orders. `task_end_of_day.py` rewrites cached data and strategy files; `task_end_of_week.py` regenerates the dev strategy snapshots (`dev_<INDICATORS_START>` … `dev_<INDICATORS>`). An empty final test writes an empty live strategies file (no trading); only `task_end_of_week.py` alerts. `src/development.py` by default regenerates the dev snapshots and overwrites `src/config/OMX_trade_strategies.json`.

## Pitfalls
- Host cron uses global `/usr/bin/python3.13`; deploy does not install dependencies, so after `uv.lock` changes re-export `requirements.txt` and pip-install it on the host (README "Deployment").
- Cron starts the live loop once; it runs until shortly after `SETTINGS.TIME.END` (cron does not invoke it every two minutes).
- [src/print_logs.sh](src/print_logs.sh) assumes the Linux host layout and GNU `date -d`.
- Logs and `daily_trading_stats_OMX.json` accumulate under `src/logs/` locally, `logs/` on the host.

## Docs And Automation
- Update `README.md` and `CLAUDE.md` with changes to `src/apis/avanza/client/client.py`, `src/config/settings.py`, `src/services/storage/operators.py`, `src/services/ta/strategies/operators.py`, `src/task_*.py`, or `deploy.yaml`; update `CLAUDE.md` with changes to `pyproject.toml`, `.pre-commit-config.yaml`, or `.claude/{hooks,agents,skills,rules}/`.
- `git push` runs two blocking gates: `documentation-alignment` (`documenter` fixes stale docs, blocks if it edited) and `code-review` (`code-reviewer`, blocks on blocking findings). Pre-check with `python3 .claude/hooks/pre_push_documentation.py --working-tree` or `pre_push_code_review.py --working-tree`; bypass once with `SKIP=<gate-id> git push`. A blocked gate prints a paste-ready Claude prompt that fixes everything, self-checks both gates, and commits; passes are recorded in `.git/claude-gates/`, so pushing identical content skips review. Details: `.claude/rules/claude-customizations.md`.
- Agents: `code-reviewer` before a deploy or PR, `documenter` for doc drift, `refactorer` only for a requested behavior-preserving cleanup. `/code-review-skill` and `/documentation-skill` run the first two in a forked context. Do not reintroduce `AGENTS.md` or Copilot customizations.
