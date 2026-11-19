# pyAvanza_v2

pyAvanza_v2 is a Python trading bot for Tesla (TSLA) BULL and BEAR certificates on Avanza, trading the US session. It caches market data, turns configured technical indicators into trading signals (a weighted multi-resolution score), backtests and paper-trades them, refreshes Avanza watchlists, and can place live orders.

## Capabilities

- Cache OHLCV history from Avanza or Yahoo Finance at minute, two-minute, five-minute, thirty-minute, hourly, and daily resolutions.
- Fit a weighted score over indicator votes on several resolutions, and walk it forward out of sample.
- Paper-trade the weighted score after each session, and refit the weighted score weekly.
- Execute a live trading loop against Avanza on the weighted score while `SETTINGS.LIVE_ORDERS` is on (currently `True`).
- Refresh watchlists and choose preferred BULL or BEAR instruments based on leverage and spread filters.
- Record transaction summaries and daily trading stats, and send alerts through `telegram-send`.

## Project Layout

- `src/task_trade.py`: live trading entry point.
- `src/task_end_of_day.py`: history cache and the paper replay of the session.
- `src/task_end_of_week.py`: weighted-score refit, paper summaries, and balance logging.
- `src/development.py`: manual helper; `mode` selects indicator tuning, the holdout check, the weighted-score walk-forward (all three write no files), or weighted-score training (currently the default; writes the model file; see Indicator Tuning).
- `src/apis/avanza/`: Avanza client, typed models, account and order operators.
- `src/apis/yahoo/`: Yahoo Finance history wrapper.
- `src/apis/telegram/`: alert delivery through `telegram-send`.
- `src/services/ta/`: indicators, their LONG/SHORT signals (`Signal`), and the per-bar signal columns.
- `src/services/trading/`: exit rules shared by the backtest and the live loop (`TrackedPosition`, `ExitLevels`).
- `src/services/storage/`: pickle-backed OHLCV cache.
- `src/services/calendar/`: NYSE market-hours helpers (times in Stockholm time).
- `src/tasks/`: the top layer: live signal loop and order execution (`trade/main.py`, `trade/states.py`), code shared by the live loop and the backtest (`shared/`: bars, coarse-bar resampling, the weighted score's `votes.py` and `weighted_model.py`), and the backtest engine (`backtest/`). Each `src/apis/*` and `src/services/*` package is isolated and never imports another; only `tasks/`, the `task_*.py` scripts, and `src/development.py` compose them.
- `tests/`: unit and integration tests, mirroring `src/` (not deployed).
- `src/config/`: runtime settings and the weighted model (`TSLA_weighted_model.json`).
- `src/utils/`: logging, shared constants, and retry backoff.

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

- `task_end_of_day.py` caches history and then replays today's session with the weighted score (see Signal Source). It writes one cache per resolution (`TSLA_1m`, `2m`, `5m`, `30m`, `60m`, `1d`); Avanza serves 1m/2m/5m/60m bars for the last session only and 30m bars by the week (refetched bars replace stored ones), so the caches grow one session per run.
- `task_end_of_week.py` refits the weighted score, sends the paper journal's running total by Telegram, and logs the current portfolio balance.
- `task_trade.py` starts one intraday loop that keeps running until shortly after `SETTINGS.TIME.END`.
- On macOS, `DRY_RUN` defaults to `True`, so local runs do not place live orders or send Telegram alerts (the message is only logged) unless you change `DRY_RUN` in `src/config/__init__.py`.

## Trading Flow

1. Cached data is loaded from `src/data/` locally or `data/` on the deployed host.
2. `src/services/ta/` builds indicators from the defaults in `src/config/settings.py`; the weighted score turns them into LONG/SHORT signals on 2m bars (see Signal Source).
3. The backtest simulator (`src/tasks/backtest/simulator.py`) plays those signals with live-loop mechanics, used by the paper replay, the walk-forward, and `development.py`:
   - Entries fill at the next bar's open. Every simulated trade pays the spread once, on the sale: the instrument is sold `SETTINGS.BACKTEST_SPREAD` below its actual price (there is no commission).
   - Exits follow the weighted score's `ExitLevels` (`WEIGHTED_LEVELS` in `src/tasks/shared/weighted_model.py`; `ExitLevels` in `src/services/trading/tracked_position.py`): an optional take-profit (a resting order, filled inside the bar), stop loss (confirmed on consecutive completed bars), and an optional holding time in completed bars. The levels and the stop loss's confirmation count (`STOP_LOSS_CONFIRMATIONS`) are set in `SETTINGS.EXITS`; the holding time is `SETTINGS.WEIGHTED_SCORE.HORIZON_BARS`.
   - Positions never carry overnight: no entry on a trading day's last bar, and open positions exit at that bar's close or at `SETTINGS.TIME.END`, whichever comes first.
4. The live loop (`src/tasks/trade/`) refreshes watchlists, evaluates the weighted score on each completed bar, and translates its signals into Avanza orders. Exits use the same levels on the underlying, checked once per completed bar (a position found without a record, e.g. after a restart, is measured from the current underlying price, and its holding time counts from then); a take-profit order scales the underlying move by the bought instrument's leverage.
5. Transactions are grouped into deals and written into daily trading stats JSON in the logs directory.

## Signal Source

`task_trade.py` trades the weighted score's signals while `SETTINGS.LIVE_ORDERS` is `True` (current setting); with `False` it only logs them as `[PAPER]` (a failure there is only logged) and places no orders (a held position then exits only at the end of the day, or when market data goes stale). The weighted score is also replayed after the close by `task_end_of_day.py` with the backtest simulator (`src/tasks/backtest/paper_trade.py`) into `paper_trades_TSLA_weighted.json` in the logs directory (re-running a session replaces its entry); `task_end_of_week.py` sends the journal's running total by Telegram. When trading live, compare the journal with `daily_trading_stats_TSLA.json`.

- `weighted` (`SETTINGS.WEIGHTED_SCORE`, `src/tasks/shared/votes.py`, `src/tasks/shared/weighted_model.py`): every indicator on every resolution votes (`dir`: +1 LONG, -1 SHORT, 0 otherwise). The defaults (30m, 60m and daily direction votes, 60-bar horizon, about a year of training, clipped target) come from a calibration on OMX (2024-11..2026-11); their TSLA walk-forward result is recorded in `settings.py`. Intraday `RESOLUTIONS` are built from the 2m cache and vote from the 2m bar that completes their bar; `USE_DAILY` adds the 1d cache's votes as of the previous session. An L1 linear fit gives each vote a weight on the underlying move over the next `HORIZON_BARS` (exit fill, capped at `TIME.END`; useless votes get 0). BULL when the weighted score is above the training `ENTRY_QUANTILE`, BEAR below its negative. Positions exit by `SETTINGS.EXITS` (currently a 15% take-profit and a 5% stop loss on the x10 instrument, chosen on calibration data and confirmed once on the holdout, recorded in `settings.py`) and are held at most `HORIZON_BARS` completed bars (the move the score predicts), then sold at the next open or at `TIME.END`; signals are ignored while a position is held (`ExitLevels.hold_bars`, shared by the backtest simulator and `Trade.stop_loss`; a position found without a record after a restart counts its holding time from then). The model is `config/TSLA_weighted_model.json` (votes, weights, thresholds), refitted on the last `TRAIN_DAYS` by `task_end_of_week.py`; weights can be edited by hand between refits. `development.py` modes: `weighted_walk_forward` (refit every 5 sessions on the data before, trade the next ones; no files written), `weighted_training` (writes the model file), and the tuning modes below.

## Indicator Tuning

`src/development.py` with `mode = "indicator_tuning"` searches one indicator's parameters, like the old per-indicator tests: an `IndicatorGrid` names `SETTINGS.INDICATORS[category][name]` and gives each parameter a list to search or a scalar to keep. Every combination, plus the current parameters and the indicator switched off, runs the weighted-score walk-forward (`src/tasks/backtest/indicator_tuning.py`, about 30 s each; `WORKERS` processes, one per CPU up to 8, run candidates in parallel and, in the single walk-forward modes, the refit periods) on the data before `HOLDOUT_START`. The table is ranked by edge: the t-statistic of the out-of-sample correlation between the score and the move it predicts, per refit period. It does not depend on entry thresholds or costs, and differences under about 1 are noise; the trade columns show the net result after `BACKTEST_SPREAD` with the current `SETTINGS.EXITS`. Copy a winner into `settings.py` by hand, tune one indicator at a time, and run `mode = "weighted_holdout"` once on the final set (the walk-forward over the sessions from `HOLDOUT_START` on). Running the holdout after every tweak turns it into calibration data.

## Data

`TSLA_2m.pickle` history before Avanza's own sessions is rebuilt: 1-minute IEX bars from 2022-03 (complete sessions, prices within 0.02% of Yahoo, but IEX volume is 1-3% of the total), with each session's volume rescaled to Yahoo's 30-minute, hourly, or daily totals and then to Avanza's intraday scale (about 0.59 of Yahoo's); Yahoo's last 2m sessions are scaled the same way. `TSLA_1d.pickle` is Yahoo/Avanza daily data (identical). `TSLA_30m` and `TSLA_60m` are resampled from that 2m history on Avanza's bar alignment; `TSLA_1m` and `TSLA_5m` reach back only as far as Yahoo serves them (about 3 and 8 weeks), scaled the same way. From 2026-11-18 on, `task_end_of_day.py` appends Avanza's own bars. The host cache has none of this history until the pickles are copied to `data/` on the host.

## Runtime Conventions

- Watchlists are expected to follow `DT_<direction>_<instrument>_<instrument_type>`, for example `DT_BULL_TSLA_CERTIFICATE`.
- Avanza names the products after the company, not the ticker (`SETTINGS.PRODUCT_NAME`, `TESLA`): watchlist updates search certificates as `<direction> TESLA X<MULTIPLIER> AVA` (`BULL TESLA X10 AVA`) and warrants as `<L|S> TESLA AVA`, and the portfolio and order lists keep only instruments whose name contains it.
- Local runs use `src/config`, `src/data`, and `src/logs`. The deploy workflow copies only the contents of `src/` to `/home/ubuntu/pyAvanza/`, so the server uses `config`, `data`, and `logs` at the remote root.
- The weighted model is persisted as `TSLA_weighted_model.json` (weights and thresholds) and read back by the live loop and the paper replay.
- Every retry is bounded and backs off exponentially (`src/utils/retry.py`). Avanza API calls other than chart data, including watchlist refresh and mutation, retry HTTP errors and empty responses up to `AVANZA_RETRY_ATTEMPTS` (default 10), waiting `AVANZA_RETRY_BACKOFF_SECONDS` (3) doubling up to `AVANZA_RETRY_BACKOFF_CAP_SECONDS` (30); only a genuinely empty, successful response from a watchlist add/remove call short-circuits that loop. Chart data uses `AVANZA_CHART_DATA_RETRY_ATTEMPTS` (120), from `AVANZA_CHART_DATA_RETRY_BACKOFF_SECONDS` (2) up to `AVANZA_CHART_DATA_RETRY_SLEEP_SECONDS` (30). Login retries `AVANZA_CONNECT_RETRY_ATTEMPTS` (10) times, from `AVANZA_CONNECT_RETRY_BACKOFF_SECONDS` (2) up to `AVANZA_CONNECT_RETRY_BACKOFF_CAP_SECONDS` (60), then raises. The live loop waits 5 s doubling up to 60 s after a connection or unknown error.

## Generated Artifacts

- `src/config/TSLA_weighted_model.json` locally and `config/TSLA_weighted_model.json` on the server: the weighted score's weights, refitted by `task_end_of_week.py`.
- `src/data/*.pickle` locally and `data/*.pickle` on the server: OHLCV cache files.
- `src/logs/*.log` locally and `logs/*.log` on the server: task logs, `daily_trading_stats_TSLA.json`, and the paper journal `paper_trades_TSLA_weighted.json`.
- `uv.lock`: committed dependency lockfile for reproducible syncs.

## Testing

```sh
uv run python -m compileall src .claude/hooks
uv run pytest
uv run pytest -m integration tests/apis/avanza/client/test_client.py
```

The integration tests require valid Avanza credentials in `src/config/.env` and can hit a live account.

## Deployment

`.github/workflows/deploy.yaml` deploys on pushes to `main`. The workflow rsyncs `src/` into `/home/ubuntu/pyAvanza/`, preserves `data`, `logs`, `config`, and `.venv`, writes `config/.env` from GitHub Secrets, and refreshes the project cron section. Files committed under `src/config/` still overwrite their host copies: each deploy replaces the host's refitted `config/TSLA_weighted_model.json` with the committed one until the next `task_end_of_week.py`.

Cron runs every task with the host's global `/usr/bin/python3.13` (installed next to the system Python, e.g. from the deadsnakes PPA). Dependencies are not installed by the workflow: export them locally with `uv export --no-dev --no-hashes --no-emit-project --frozen -o requirements.txt`, copy the file to the host, and run `sudo python3.13 -m pip install -r requirements.txt` whenever `uv.lock` changes. The workflow fails before updating cron if `/usr/bin/python3.13` is missing.

The current cron contract starts:

- `task_end_of_day.py` at `22:10` on weekdays
- `task_end_of_week.py` at `09:00` on Saturdays
- `task_trade.py` at `16:13` on weekdays (the trading window is `16:15`-`21:45` Stockholm time)
- a stats copy job every 10 minutes from `15:00` through `22:59` on weekdays

All times are the host's Stockholm time. The US session is `15:30`-`22:00` there, except in the weeks the US and European clock changes differ (`14:30`-`21:00`), when the NYSE close from `src/services/calendar/` ends the day early.

`src/print_logs.sh` is intended for the deployed Linux host; it tails the trade log and relies on GNU `date -d`.
