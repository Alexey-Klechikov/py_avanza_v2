# pyAvanza_v2

pyAvanza_v2 is a Python trading bot for OMX-linked BULL and BEAR products on Avanza. It caches market data, turns configured technical indicators into trading signals (a fixed 30-minute rule and a weighted multi-resolution score), backtests and paper-trades them, refreshes Avanza watchlists, and can place live orders.

## Capabilities

- Cache OHLCV history from Avanza or Yahoo Finance at minute, two-minute, five-minute, hourly, and daily resolutions.
- Fit a weighted score over indicator votes on several resolutions, and walk it forward out of sample.
- Paper-trade every signal source after each session, and refit the weighted score weekly.
- Execute a live trading loop against Avanza with the source chosen in `SETTINGS.LIVE_SIGNAL_SOURCE` (none by default).
- Refresh watchlists and choose preferred BULL or BEAR instruments based on leverage and spread filters.
- Record transaction summaries and daily trading stats, and send alerts through `telegram-send`.

## Project Layout

- `src/task_trade.py`: live trading entry point.
- `src/task_end_of_day.py`: history cache and the paper replay of the session.
- `src/task_end_of_week.py`: weighted-score refit, paper summaries, and balance logging.
- `src/development.py`: manual helper; `mode` selects the weighted-score walk-forward (default, no files written), weighted-score training, or the fixed-rule replay.
- `src/apis/avanza/`: Avanza client, typed models, account and order operators.
- `src/apis/yahoo/`: Yahoo Finance history wrapper.
- `src/apis/telegram/`: alert delivery through `telegram-send`.
- `src/services/ta/`: indicators, indicator combinations (`Strategy`) and their per-bar signals.
- `src/services/trading/`: exit rules shared by the backtest and the live loop (`TrackedPosition`, `ExitLevels`).
- `src/services/storage/`: pickle-backed OHLCV cache, data windows, and candle-quality checks.
- `src/services/calendar/`: Stockholm market-hours helpers.
- `src/tasks/`: the top layer: live signal loop and order execution (`trade/main.py`, `trade/states.py`), the fixed rule and weighted score signal sources (`fixed_rule.py`; weighted score in `backtest/votes.py`, `backtest/model.py`), and the backtest engine (`backtest/`). Each `src/apis/*` and `src/services/*` package is isolated and never imports another; only `tasks/`, the `task_*.py` scripts, and `src/development.py` compose them.
- `tests/`: unit and integration tests, mirroring `src/` (not deployed).
- `src/config/`: runtime settings and the weighted model (`OMX_weighted_model.json`).
- `src/utils/`: logging and shared constants.

## Requirements

- Python `3.13`
- `uv`
- A writable `src/data/` directory for local cache files
- Avanza credentials stored in `src/config/.env` for local runs:

```dotenv
AVA_USERNAME=...
AVA_PASS=...
AVA_TOTP=...
```

- Optional machine-level `telegram-send` configuration if you want task alerts

## Quick Start

```sh
uv sync
mkdir -p src/data
uv run python -m compileall src .claude/hooks
uv run pytest tests/apis/yahoo/client/models/test_history_request.py
```

## Running the Tasks

```sh
uv run python src/task_end_of_day.py
uv run python src/task_end_of_week.py
uv run python src/task_trade.py
uv run python src/development.py
```

- `task_end_of_day.py` caches history and then replays today's session with each signal source (see Signal Sources).
- `task_end_of_week.py` refits the weighted score, sends the paper journals' running totals by Telegram, and logs the current portfolio balance.
- `task_trade.py` starts one intraday loop that keeps running until shortly after `SETTINGS.TIME.END`.
- On macOS, `DRY_RUN` defaults to `True`, so local runs do not place live orders or send Telegram alerts (the message is only logged) unless you change `DRY_RUN` in `src/config/__init__.py`.

## Trading Flow

1. Cached data is loaded from `src/data/` locally or `data/` on the deployed host.
2. `src/services/ta/` builds indicators from the defaults in `src/config/settings.py`; each signal source turns them into LONG/SHORT/EXIT signals on 2m bars (see Signal Sources).
3. The backtest simulator (`src/tasks/backtest/simulator.py`) plays those signals with live-loop mechanics, used by the paper replay, the walk-forward, and `development.py`:
   - Entries fill at the next bar's open. Every simulated trade pays the spread once, on the sale: the instrument is sold `SETTINGS.SPREAD_DEFAULT` below its actual price (there is no commission).
   - Exits follow the source's `ExitLevels` (`src/services/trading/tracked_position.py`): an optional take-profit (a resting order, filled inside the bar), stop loss and pullback (confirmed on consecutive completed bars, `SETTINGS.STOP_LOSS`, `SETTINGS.PULLBACK`), and an optional holding time in completed bars.
   - Positions never carry overnight: no entry on a trading day's last bar, and open positions exit at that bar's close or at `SETTINGS.TIME.END`, whichever comes first.
4. The live loop (`src/tasks/trade/`) refreshes watchlists, evaluates every signal source on each completed bar, and translates the live source's signals into Avanza orders. Exits use the same levels on the underlying, checked once per completed bar (a position found without a record, e.g. after a restart, is measured from the current underlying price, and its holding time counts from then); a take-profit order scales the underlying move by the bought instrument's leverage.
5. Transactions are grouped into deals and written into daily trading stats JSON in the logs directory.

## Signal Sources

`task_trade.py` trades the source named by `SETTINGS.LIVE_SIGNAL_SOURCE` (default `None`: no orders) and logs the others' signals as `[PAPER]` (a failure there never reaches the live source). Positions use the live source's exit levels. Every source is also replayed after the close by `task_end_of_day.py` with the backtest simulator (`src/tasks/backtest/paper_trade.py`) into `paper_trades_OMX_<source>.json` in the logs directory (re-running a session replaces its entry); `task_end_of_week.py` sends each journal's running total by Telegram. When trading a source live, compare its journal with `daily_trading_stats_OMX.json`.

- `fixed_rule` (`SETTINGS.FIXED_RULE`, `src/tasks/fixed_rule.py`): one rule frozen on `START`: the `STRATEGY` indicators on `SIGNAL_RESOLUTION` (30-minute) bars built from the 2m cache, faded when `INVERTED`, acting on the 2m bar that completes each coarse bar (a coarse bar still in progress never signals), with its own exit levels. `development.py` (`mode = "fixed_rule"`) logs its result per quarter over the cache. Do not change the rule while it is being tested.
- `weighted` (`SETTINGS.WEIGHTED_SCORE`, `src/tasks/backtest/votes.py`, `src/tasks/backtest/model.py`): every indicator on every resolution votes (`dir`: +1 LONG, -1 SHORT; `exit`: 1 on EXIT, only with `USE_EXIT_VOTES`). The defaults (30m, 60m and daily direction votes, 60-bar horizon, about a year of training, clipped target) come from a calibration on 2024-11..2025-12 confirmed on 2026, recorded in `settings.py`. Intraday `RESOLUTIONS` are built from the 2m cache and vote from the 2m bar that completes their bar; `USE_DAILY` adds the 1d cache's votes as of the previous session. An L1 linear fit gives each vote a weight on the underlying move over the next `HORIZON_BARS` (exit fill, capped at `TIME.END`; useless votes get 0). BULL when the weighted score is above the training `ENTRY_QUANTILE`, BEAR below its negative. Positions are time-boxed, as calibrated: held exactly `HORIZON_BARS` completed bars (the move the score predicts), then sold at the next open or at `TIME.END`, with no take-profit, stop-loss, or pullback exit, and signals are ignored while a position is held (`ExitLevels.hold_bars`, shared by the backtest simulator and `Trade.stop_loss`; a position found without a record after a restart counts its holding time from then). The model is `config/OMX_weighted_model.json` (votes, weights, thresholds), refitted on the last `TRAIN_DAYS` by `task_end_of_week.py`; weights can be edited by hand between refits. `development.py` modes: `weighted_walk_forward` (refit every 5 sessions on the data before, trade the next ones; no files written) and `weighted_training` (writes the model file).

## Runtime Conventions

- Watchlists are expected to follow `DT_<direction>_<instrument>_<instrument_type>`, for example `DT_BULL_OMX_CERTIFICATE`.
- Local runs use `src/config`, `src/data`, and `src/logs`. The deploy workflow copies only the contents of `src/` to `/home/ubuntu/pyAvanza/`, so the server uses `config`, `data`, and `logs` at the remote root.
- The weighted model is persisted as `OMX_weighted_model.json` (weights and thresholds) and read back by the live loop and the paper replay.
- Avanza API calls other than chart data, including watchlist refresh and mutation, retry HTTP errors and empty responses up to `AVANZA_RETRY_ATTEMPTS` (default 10) before giving up; only a genuinely empty, successful response from a watchlist add/remove call short-circuits that retry loop. Chart data uses its own `AVANZA_CHART_DATA_RETRY_ATTEMPTS` (default 120).

## Generated Artifacts

- `src/config/OMX_weighted_model.json` locally and `config/OMX_weighted_model.json` on the server: the weighted score's weights, refitted by `task_end_of_week.py`.
- `src/data/*.pickle` locally and `data/*.pickle` on the server: OHLCV cache files.
- `src/logs/*.log` locally and `logs/*.log` on the server: task logs, `daily_trading_stats_OMX.json`, and the paper journals `paper_trades_OMX_<source>.json`.
- `uv.lock`: committed dependency lockfile for reproducible syncs.

## Testing

```sh
uv run python -m compileall src .claude/hooks
uv run pytest
uv run pytest -m integration tests/apis/avanza/client/test_client.py
```

The integration tests require valid Avanza credentials in `src/config/.env` and can hit a live account.

## Deployment

`.github/workflows/deploy.yaml` deploys on pushes to `main`. The workflow rsyncs `src/` into `/home/ubuntu/pyAvanza/`, preserves `data`, `logs`, `config`, and `.venv`, writes `config/.env` from GitHub Secrets, and refreshes the project cron section. Files committed under `src/config/` still overwrite their host copies: each deploy replaces the host's refitted `config/OMX_weighted_model.json` with the committed one until the next `task_end_of_week.py`.

Cron runs every task with the host's global `/usr/bin/python3.13` (installed next to the system Python, e.g. from the deadsnakes PPA). Dependencies are not installed by the workflow: export them locally with `uv export --no-dev --no-hashes --no-emit-project --frozen -o requirements.txt`, copy the file to the host, and run `sudo python3.13 -m pip install -r requirements.txt` whenever `uv.lock` changes. The workflow fails before updating cron if `/usr/bin/python3.13` is missing.

The current cron contract starts:

- `task_end_of_day.py` at `22:10` on weekdays
- `task_end_of_week.py` at `09:00` on Saturdays
- `task_trade.py` at `09:43` on weekdays
- a stats copy job every 10 minutes from `12:00` through `18:59` on weekdays

`src/print_logs.sh` is intended for the deployed Linux host; it tails the trade log and relies on GNU `date -d`.
