# pyAvanza_v2

pyAvanza_v2 is a Python trading bot for OMX-linked BULL and BEAR products on Avanza. It caches market data, builds technical-analysis strategies from configured indicators, backtests them, refreshes Avanza watchlists, and can place live orders with stop-loss, take-profit, and pullback exits.

## Capabilities

- Cache OHLCV history from Avanza or Yahoo Finance at minute, two-minute, five-minute, hourly, and daily resolutions.
- Generate, extend, and rank multi-indicator strategies into `OMX_trade_strategies*.json` snapshots.
- Run scheduled end-of-day and end-of-week backtests.
- Execute a live trading loop against Avanza using the highest-ranked stored strategies.
- Refresh watchlists and choose preferred BULL or BEAR instruments based on leverage and spread filters.
- Record transaction summaries and daily trading stats, and send alerts through `telegram-send`.

## Project Layout

- `src/task_trade.py`: live trading entry point.
- `src/task_end_of_day.py`: history cache and end-of-day backtest flow.
- `src/task_end_of_week.py`: weekly strategy regeneration and balance logging.
- `src/development.py`: manual strategy-generation and indicator-tuning helper.
- `src/apis/avanza/`: Avanza client, typed models, account and order operators, and trade execution helpers.
- `src/apis/yahoo/`: Yahoo Finance history wrapper.
- `src/apis/telegram/`: alert delivery through `telegram-send`.
- `src/services/ta/`: indicators, plots, strategy composition, and strategy persistence.
- `src/services/storage/`: pickle-backed OHLCV cache.
- `src/services/calendar/`: Stockholm market-hours helpers.
- `src/tasks/trade_strategies/`: live signal loop and backtest engine.
- `src/config/`: runtime settings and generated strategy ranking files.
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
uv run python -m compileall src .github/hooks/scripts
uv run pytest src/apis/yahoo/client/models/history_request_test.py
```

## Running the Tasks

```sh
uv run python src/task_end_of_day.py
uv run python src/task_end_of_week.py
uv run python src/task_trade.py
uv run python src/development.py
```

- `task_end_of_day.py` caches history and reruns backtests against recent data.
- `task_end_of_week.py` rebuilds the dev strategy snapshots and logs the current portfolio balance.
- `task_trade.py` starts one intraday loop that keeps running until shortly after `SETTINGS.TIME.END`.
- On macOS, `TradeStrategies.DRY_RUN` defaults to `True`, so local runs do not place live orders unless you change `src/config/settings.py`.

## Trading Flow

1. Cached data is loaded from `src/data/` locally or `data/` on the deployed host.
2. `src/services/ta/` builds indicators from the defaults in `src/config/settings.py`.
3. Backtests rank strategies and write `OMX_trade_strategies*.json` snapshots.
4. The live loop loads the top strategies, refreshes watchlists, and translates signals into Avanza orders.
5. Transactions are grouped into deals and written into daily trading stats JSON in the logs directory.

## Runtime Conventions

- Watchlists are expected to follow `DT_<direction>_<instrument>_<instrument_type>`, for example `DT_BULL_OMX_CERTIFICATE`.
- Local runs use `src/config`, `src/data`, and `src/logs`. The deploy workflow copies only the contents of `src/` to `/home/ubuntu/pyAvanza/`, so the server uses `config`, `data`, and `logs` at the remote root.
- Strategy rankings are persisted as `OMX_trade_strategies*.json` and are read back by the live trading loop.

## Generated Artifacts

- `src/config/OMX_trade_strategies*.json` locally and `config/OMX_trade_strategies*.json` on the server: ranked strategy snapshots.
- `src/data/*.pickle` locally and `data/*.pickle` on the server: OHLCV cache files.
- `src/logs/*.log` locally and `logs/*.log` on the server: task logs and `daily_trading_stats_OMX.json`.
- `uv.lock`: committed dependency lockfile for reproducible syncs.

## Testing

```sh
uv run python -m compileall src .github/hooks/scripts
uv run pytest
uv run pytest -m integration src/apis/avanza/client/client_test.py
```

The integration tests require valid Avanza credentials in `src/config/.env` and can hit a live account.

## Deployment

`.github/workflows/deploy.yaml` deploys on pushes to `main`. The workflow rsyncs `src/` into `/home/ubuntu/pyAvanza/`, preserves `data`, `logs`, `config`, and `.venv`, writes `config/.env` from GitHub Secrets, and refreshes the project cron section.

The current cron contract starts:

- `task_end_of_day.py` at `22:10` on weekdays
- `task_end_of_week.py` at `09:00` on Saturdays
- `task_trade.py` at `09:43` on weekdays
- a stats copy job every 10 minutes from `12:00` through `18:59` on weekdays

`src/print_logs.sh` is intended for the deployed Linux host; it tails the trade log and relies on GNU `date -d`.
