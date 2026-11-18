# pyAvanza_v2

Python 3.13 trading bot: caches OHLCV data, turns TA indicators into signal sources (fixed 30m rule, weighted multi-resolution score), paper-trades them, runs a live Avanza loop that can place real orders. Overview, runtime, and deploy flow: [README.md](README.md).

## Setup
- `uv sync` (interpreter pinned in `.python-version`, repo-local `.venv`). Create `src/data/` first: `Storage.write()` in `src/services/storage/operators.py` does not create it.
- Credentials (`AVA_USERNAME`, `AVA_PASS`, `AVA_TOTP`): `src/config/.env` locally, `config/.env` on the host (written by the deploy workflow from GitHub Secrets).

## Map
- [src/task_trade.py](src/task_trade.py) live entry → [src/tasks/trade/main.py](src/tasks/trade/main.py) loop (cached data, signal sources → `FlowAction`, flow control) → `src/tasks/trade/states.py` (`Trade`: live orders, exit levels). `Direction`, `FlowAction`, `SignalSource`: `src/tasks/trade/models.py`.
- `src/tasks/backtest/`: `simulator.py` (`BarSimulator`, live-loop mechanics), `paper_trade.py` (paper journals), weighted score `votes.py`, `model.py`, `weighted_walk_forward.py`; `src/tasks/fixed_rule.py`, `src/tasks/coarse_bars.py`.
- [src/task_end_of_day.py](src/task_end_of_day.py), [src/task_end_of_week.py](src/task_end_of_week.py): cache, paper replay, weekly refit. Signal sources (README "Signal Sources"): `SETTINGS.FIXED_RULE` (`src/tasks/fixed_rule.py`), `SETTINGS.WEIGHTED_SCORE` (`src/tasks/backtest/votes.py`, `model.py`, model `config/OMX_weighted_model.json`, refitted by end of week); `SETTINGS.LIVE_SIGNAL_SOURCE` picks the one the live loop trades (default `None`: no orders), the rest are `[PAPER]`; end of day replays them into `paper_trades_OMX_<source>.json` (`tasks/backtest/paper_trade.py`).
- `src/apis/{avanza,yahoo,telegram}/`: `client/` adapts payloads and retries (shapes in `client/models/`; Avanza auth in `src/apis/avanza/client/client.py`); `operators/` holds repo workflows (`watchlists.py`, `orders.py`, `portfolio.py`, `transactions.py`).
- `src/services/ta/`: indicators (`operators.get_indicators`), indicator combinations (`Strategy`, `Signal`, signal marking in `strategies/signals.py`). `services/trading/`: exit rules shared by backtest and live loop (`TrackedPosition`, `ExitLevels`). `services/storage/`: OHLCV cache (a new fetch replaces the stored candle with the same timestamp), `windows.py` (`DataWindow`). `services/calendar/`: Stockholm market hours.
- [src/config/settings.py](src/config/settings.py): trading window, risk controls, multiplier, backtest spread, signal sources (`FIXED_RULE`, `WEIGHTED_SCORE`, `LIVE_SIGNAL_SOURCE`), indicator parameters. `src/utils/`: logging, constants.
- [.github/workflows/deploy.yaml](.github/workflows/deploy.yaml): remote layout and cron (the only file under `.github/`). `.claude/`: agents, path-scoped rules, skills, pre-push hooks.

## Conventions
- `src/task_*.py` and `src/development.py` stay thin: set handlers, call operators/tasks, own top-level exception and alert handling.
- Layers: each `apis/<name>` and each `services/<name>` is isolated and imports only itself, `config`, and `utils` (never another `apis/*` or `services/*` branch, nor `tasks`); `config`/`utils` import no layer; `tasks/`, `task_*.py`, and `development.py` compose everything. `tests/test_architecture.py` enforces this.
- `src/apis/*/client/` only adapts third-party payloads and retries; repo-specific workflows live in `src/apis/*/operators/`; signal logic and TA never live in `apis/`.
- `services/**` has no broker/account side effects; live trading stays in `tasks/trade/main.py` and `tasks/trade/states.py`.
- Imports use the flat roots under `src/` (`apis`, `config`, `services`, `tasks`, `utils`), never `src.`; `src/` is the path root for scripts and pytest (`pythonpath = ["src"]`). Keep `__init__.py` files empty, no barrel re-exports.
- Dual paths: local `src/config`, `src/data`, `src/logs`; host `config`, `data`, `logs` (deploy syncs only the contents of `src/` to `/home/ubuntu/pyAvanza/`). Preserve both.
- `src/config/OMX_weighted_model.json` is generated (`WeightedModel`) by `task_end_of_week.py` / `development.py` and read by the live loop and paper replay; preserve its schema and name. Weights may be hand-edited between refits.
- Watchlist names are `DT_<direction>_<instrument>_<instrument_type>`; change `WatchlistNameComposition` and the operators together.
- Alerts call `telegram-send` directly (machine-level config, fails at send time; no setting in `settings.py`); under `DRY_RUN` (`src/config/__init__.py`) they are only logged.
- Python style, nesting, and complexity: `.claude/rules/pyavanza-python.md`.

## Validation
- Fast check: `uv run python -m compileall src .claude/hooks`. Types: `uvx pyright` (config `[tool.pyright]` in `pyproject.toml`, also read by Pylance; dev dependency `pandas-stubs` matches the stubs Pylance bundles). Bar frames are typed through `bar_index()` in `tasks/backtest/bars.py`. Focused: `uv run pytest <path>`. Suite: `uv run pytest`. Dependencies: `uv lock`.
- Tests live in `tests/`, mirroring `src/` (`tests/<package>/test_<module>.py`); pytest uses `testpaths = ["tests"]`, `--import-mode=importlib`, and skips `integration` tests unless run with `-m integration`. Everything except `tests/apis/avanza/client/test_client.py` is credential-free; that file is integration coverage that needs `src/config/.env` and can hit the live account.
- Never run `src/task_trade.py` to validate: `DRY_RUN` is `False` outside Darwin, so it can place live orders. `task_end_of_day.py` rewrites cached data and the paper journals; `task_end_of_week.py` rewrites `config/OMX_weighted_model.json` and sends a Telegram summary. `src/development.py` by default runs the weighted-score walk-forward (no files written); `mode = "weighted_training"` writes the weighted model.

## Pitfalls
- Host cron uses global `/usr/bin/python3.13`; deploy does not install dependencies, so after `uv.lock` changes re-export `requirements.txt` and pip-install it on the host (README "Deployment").
- Cron starts the live loop once; it runs until shortly after `SETTINGS.TIME.END` (cron does not invoke it every two minutes).
- [src/print_logs.sh](src/print_logs.sh) assumes the Linux host layout and GNU `date -d`.
- Logs, `daily_trading_stats_OMX.json`, and `paper_trades_OMX_<source>.json` accumulate under `src/logs/` locally, `logs/` on the host.

## Docs And Automation
- Update `README.md` and `CLAUDE.md` with changes to `src/apis/avanza/client/client.py`, `src/config/settings.py`, `src/services/storage/operators.py`, `src/tasks/backtest/model.py`, `src/task_*.py`, or `deploy.yaml`; update `CLAUDE.md` with changes to `pyproject.toml`, `.pre-commit-config.yaml`, or `.claude/{hooks,agents,skills,rules}/`.
- `git push` runs two blocking gates: `documentation-alignment` (`documenter` fixes stale docs, blocks if it edited) and `code-review` (`code-reviewer`, blocks on blocking findings). Pre-check with `python3 .claude/hooks/pre_push_documentation.py --working-tree` or `pre_push_code_review.py --working-tree`; bypass once with `SKIP=<gate-id> git push`. A blocked gate prints a paste-ready Claude prompt that fixes everything, self-checks both gates, and commits; passes are recorded in `.git/claude-gates/`, so pushing identical content skips review. Details: `.claude/rules/claude-customizations.md`.
- Agents: `code-reviewer` before a deploy or PR, `documenter` for doc drift, `refactorer` only for a requested behavior-preserving cleanup. `/code-review-skill` and `/documentation-skill` run the first two in a forked context. Do not reintroduce `AGENTS.md` or Copilot customizations.
