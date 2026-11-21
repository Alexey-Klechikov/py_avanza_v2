# pyAvanza_v2

Python 3.13 trading bot: caches OHLCV data, turns TA indicators into a weighted multi-resolution score, paper-trades it, runs a live Avanza loop that can place real orders. Overview, runtime, and deploy flow: [README.md](README.md).

## Setup
- `uv sync` (interpreter pinned in `.python-version`, repo-local `.venv`). Create `src/data/` first: `Storage.write()` in `src/services/storage/operators.py` does not create it.
- Credentials (`AVA_USERNAME`, `AVA_PASS`, `AVA_TOTP`): `src/config/.env` locally, `config/.env` on the host (written by the deploy workflow from GitHub Secrets).

## Map
- [src/task_trade.py](src/task_trade.py) live entry → [src/tasks/trade/main.py](src/tasks/trade/main.py) loop (cached data, weighted signal → `FlowAction`, flow control) → `src/tasks/trade/states.py` (`Trade`: live orders, exit levels). `Direction`, `FlowAction`: `src/tasks/trade/models.py`.
- `src/tasks/shared/`: what the live loop and the backtest both use: `bars.py` (`BAR_DURATION`, `bar_index`, execution columns, and the trading-window rule `is_in_trading_window`: a bar counts by its end time, as the live loop decides just after a bar closes; the live loop is the source of truth and the backtest follows it), weighted score `votes.py` and `weighted_model.py` (`WeightedModel`, fit, signals, `WEIGHTED_LEVELS`). `src/tasks/backtest/`: `simulator.py` (`BarSimulator`, live-loop mechanics), `paper_trade.py` (paper journal), `weighted_walk_forward.py`, `indicator_tuning.py` (grid search scored by walk-forward edge). `src/tasks/shared/coarse_bars.py` builds coarse bars from 2m bars; `src/utils/retry.py` the shared exponential backoff.
- [src/task_end_of_day.py](src/task_end_of_day.py), [src/task_end_of_week.py](src/task_end_of_week.py): cache, paper replay, weekly refit. Signal source (README "Signal Source"): `SETTINGS.WEIGHTED_SCORE` (`src/tasks/shared/votes.py`, `weighted_model.py`, model `config/TSLA_weighted_model.json`, refitted by end of week; signals at the top 15% of training scores, `ENTRY_QUANTILE` 0.85); `SETTINGS.LIVE_ORDERS` (currently `True`) `True` makes the live loop trade it, `False` only logs its signals as `[PAPER]`; end of day replays it into `paper_trades_TSLA_weighted.json` (`tasks/backtest/paper_trade.py`).
- `src/apis/{avanza,yahoo,telegram}/`: `client/` adapts payloads and retries (shapes in `client/models/`; Avanza auth in `src/apis/avanza/client/client.py`); `operators/` holds repo workflows (`watchlists.py`, `orders.py`, `portfolio.py`, `transactions.py`).
- `src/services/ta/`: indicators (`operators.add_indicators`), their LONG/SHORT `Signal`, per-bar signal columns (`strategies/signals.py`). `services/trading/`: exit rules shared by backtest and live loop (`TrackedPosition`, `ExitLevels`). `services/storage/`: OHLCV cache (a new fetch replaces the stored candle with the same timestamp). `services/calendar/`: NYSE market hours in Stockholm time. `SETTINGS.TIME` is the trading window within the US session, in Stockholm time.
- [src/config/settings.py](src/config/settings.py): trading window, risk controls, multiplier, backtest spread, signal source (`WEIGHTED_SCORE`, `LIVE_ORDERS`), indicator parameters. `src/utils/`: logging, constants, retry backoff.
- [.github/workflows/deploy.yaml](.github/workflows/deploy.yaml): remote layout and cron (the only file under `.github/`). `.claude/`: agents, path-scoped rules, skills, pre-push hooks.

## Conventions
- `src/task_*.py` and `src/development.py` stay thin: set handlers, call operators/tasks, own top-level exception and alert handling.
- Layers: each `apis/<name>` and each `services/<name>` is isolated and imports only itself, `config`, and `utils` (never another `apis/*` or `services/*` branch, nor `tasks`); `config`/`utils` import no layer; `tasks/`, `task_*.py`, and `development.py` compose everything. `tests/test_architecture.py` enforces this.
- `src/apis/*/client/` only adapts third-party payloads and retries; repo-specific workflows live in `src/apis/*/operators/`; signal logic and TA never live in `apis/`.
- `services/**` has no broker/account side effects; live trading stays in `tasks/trade/main.py` and `tasks/trade/states.py`.
- Imports use the flat roots under `src/` (`apis`, `config`, `services`, `tasks`, `utils`), never `src.`; `src/` is the path root for scripts and pytest (`pythonpath = ["src"]`). Keep `__init__.py` files empty, no barrel re-exports.
- Dual paths: local `src/config`, `src/data`, `src/logs`; host `config`, `data`, `logs` (deploy syncs only the contents of `src/` to `/home/ubuntu/pyAvanza/`). Preserve both.
- `src/config/TSLA_weighted_model.json` is generated (`WeightedModel`) by `task_end_of_week.py` / `development.py` and read by the live loop and paper replay; preserve its schema and name. Weights may be hand-edited between refits.
- Watchlist names are `DT_<direction>_<instrument>_<instrument_type>`; change `WatchlistNameComposition` and the operators together.
- Alerts call `telegram-send` directly (machine-level config, fails at send time; no setting in `settings.py`); under `DRY_RUN` (`src/config/__init__.py`) they are only logged.
- Python style, nesting, and complexity: `.claude/rules/pyavanza-python.md`.

## Validation
- Fast check: `uv run python -m compileall src .claude/hooks`. Types: `uvx pyright` (config `[tool.pyright]` in `pyproject.toml`, also read by Pylance; dev dependency `pandas-stubs` matches the stubs Pylance bundles). Bar frames are typed through `bar_index()` in `tasks/shared/bars.py`. Focused: `uv run pytest <path>`. Suite: `uv run pytest`. Dependencies: `uv lock`.
- Tests live in `tests/`, mirroring `src/` (`tests/<package>/test_<module>.py`); pytest uses `testpaths = ["tests"]`, `--import-mode=importlib`, and skips `integration` tests unless run with `-m integration`. Everything except `tests/apis/avanza/client/test_client.py` is credential-free; that file is integration coverage that needs `src/config/.env` and can hit the live account.
- Never run `src/task_trade.py` to validate: `DRY_RUN` is `False` outside Darwin, so it can place live orders. `task_end_of_day.py` rewrites cached data and the paper journals; `task_end_of_week.py` rewrites `config/TSLA_weighted_model.json` and sends a Telegram summary. `src/development.py` currently defaults to `mode = "weighted_training"`, which writes the weighted model; `indicator_tuning` (`tasks/backtest/indicator_tuning.py`, README "Indicator Tuning") and the walk-forward modes write no files.

## Pitfalls
- Host cron uses global `/usr/bin/python3.13`; deploy does not install dependencies, so after `uv.lock` changes re-export `requirements.txt` and pip-install it on the host (README "Deployment").
- `src/config/TSLA_weighted_model.json` is committed, so every deploy's rsync overwrites the host's weekly refit with the committed copy.
- `pandas_ta` 0.4.71b0 computes CCI (missing parentheses) and STC (frozen whenever MACD is negative) wrongly; `services/ta/indicators/momentum.py` computes both itself. It also silently drops keywords it does not know: STC's `tclength` (now computed in-house) and ADX's `lensig` (passed as `signal_length`, which also names the `ADX_<n>` column). Regression tests in `tests/services/ta/indicators/`. Before trusting a library call, check its keywords against the function's signature and its firing rate.
- The host runs on Stockholm time: Avanza chart timestamps use the host's local time and Yahoo bars are converted to Stockholm time, so both agree only there.
- Cron starts the live loop once; it runs until shortly after `SETTINGS.TIME.END` (cron does not invoke it every two minutes).
- [src/print_logs.sh](src/print_logs.sh) assumes the Linux host layout and GNU `date -d`.
- Logs, `daily_trading_stats_TSLA.json`, and `paper_trades_TSLA_weighted.json` accumulate under `src/logs/` locally, `logs/` on the host.

## Docs And Automation
- Update `README.md` and `CLAUDE.md` with changes to `src/apis/avanza/client/client.py`, `src/config/settings.py`, `src/services/storage/operators.py`, `src/tasks/shared/weighted_model.py`, `src/task_*.py`, or `deploy.yaml`; update `CLAUDE.md` with changes to `pyproject.toml`, `.pre-commit-config.yaml`, or `.claude/{hooks,agents,skills,rules}/`.
- `git push` runs two blocking gates: `documentation-alignment` (`documenter` fixes stale docs, blocks if it edited) and `code-review` (`code-reviewer`, blocks on blocking findings). Pre-check with `python3 .claude/hooks/pre_push_documentation.py --working-tree` or `pre_push_code_review.py --working-tree`; bypass once with `SKIP=<gate-id> git push`. A blocked gate prints a paste-ready Claude prompt that fixes everything, self-checks both gates, and commits; passes are recorded in `.git/claude-gates/`, so pushing identical content skips review. Details: `.claude/rules/claude-customizations.md`.
- Agents: `code-reviewer` before a deploy or PR, `documenter` for doc drift, `refactorer` only for a requested behavior-preserving cleanup (logic gaps, layer and domain structure, dead code, comments and names). `/code-review-skill` and `/documentation-skill` run the first two in a forked context. Do not reintroduce `AGENTS.md` or Copilot customizations.
