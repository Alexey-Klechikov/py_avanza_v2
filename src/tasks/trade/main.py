from datetime import datetime, timedelta
from http.client import RemoteDisconnected
from time import sleep

import numpy as np
import pandas as pd
from avanza.constants import Resolution, TimePeriod

from apis.avanza.client.client import get_client
from apis.avanza.operators.chart import Chart
from apis.avanza.operators.orders import Orders
from apis.avanza.operators.portfolio import Portfolio
from apis.avanza.operators.transactions import Transactions
from apis.avanza.operators.watchlists import Watchlists
from apis.yahoo.client.models.history_request import Interval, Period
from apis.yahoo.operators.ticker import Ticker
from config import DRY_RUN, SETTINGS
from services.calendar.operators import get_trading_end_time, is_market_closed
from services.storage.operators import Storage
from services.ta.strategies.models.signal import Signal
from services.trading.tracked_position import ExitLevels
from tasks.shared.bars import BAR_DURATION, bar_index
from tasks.shared.weighted_model import WEIGHTED_LEVELS, WeightedModel, load_model, weighted_signal
from tasks.trade.models import Direction, FlowAction
from tasks.trade.states import Trade
from utils.constants import TODAY_MIDNIGHT
from utils.logger.operators import get_logger
from utils.retry import backoff_seconds

log = get_logger()

# Loop-level retries after a connection or unknown error: wait before the next pass instead of hammering Avanza
RETRY_BASE_SECONDS = 5
RETRY_CAP_SECONDS = 60

HISTORY_DAYS = SETTINGS.WEIGHTED_SCORE.WARMUP_DAYS

# Turbo and mini warrant leverage drifts with the underlying (about 1% of TSLA moves an x11 turbo's leverage by 1),
# so the watchlists filled at the start drop instruments that come into range later; rebuild them while flat
WATCHLIST_UPDATE_INTERVAL = timedelta(minutes=30)

# What each signal does to the held directions: (directions to sell, direction to buy)
SIGNAL_ORDERS: dict[Signal, tuple[list[Direction], Direction | None]] = {
    Signal.LONG: ([Direction.BEAR], Direction.BULL),
    Signal.SHORT: ([Direction.BULL], Direction.BEAR),
}


class MarketData:
    """Recent 2-minute bars of the underlying, refreshed every bar, and the weighted score evaluated on them.

    `bars` covers the last few days (prices for orders and exits); `history` reaches HISTORY_DAYS back for the
    weighted score, which also uses the 1d cache (`daily`, refreshed only at end of day) and the weighted model.
    """

    def __init__(self) -> None:
        self.bars: pd.DataFrame = pd.DataFrame()
        self.history: pd.DataFrame = pd.DataFrame()
        self.daily: pd.DataFrame = pd.DataFrame()
        self.weighted_model: WeightedModel | None = None
        self.weighted_score: float | None = None
        self.is_new = False
        self.too_old = False

    def refresh(self) -> None:
        storage = Storage()

        bars = storage.read()

        if (datetime.now() - bars.index[-1]).total_seconds() < 2 * 60:  # type: ignore
            self.too_old = False
            self.is_new = True

        else:
            new_bars = _fetch_today_bars()
            if new_bars is None:
                raise ValueError("No data fetched")

            storage.write(new_bars)

            bars_count_before = bars.shape[0]
            bars = storage.read()

            self.too_old = (datetime.now() - bars.index[-1]).total_seconds() > 15 * 60
            self.is_new = bars_count_before != bars.shape[0]

        self.history = bars.loc[bars.index >= TODAY_MIDNIGHT - timedelta(days=HISTORY_DAYS)]
        self.bars = self.history.loc[self.history.index >= TODAY_MIDNIGHT - timedelta(days=4)]

    def weighted_signal(self) -> Signal | None:
        """The weighted score's signal on the last complete bar."""
        closed_history = self.history.loc[bar_index(self.history) + BAR_DURATION <= pd.Timestamp.now()]
        if self.daily.empty:
            self.daily = Storage(resolution="1d").read()

        reading = weighted_signal(self.load_weighted_model(), closed_history, self.daily)
        self.weighted_score = reading.score
        log.debug(f"Current score {reading.score:+.2f}")
        return reading.signal

    def load_weighted_model(self) -> WeightedModel:
        """The weighted model, read once per run; logs the score range that signals."""
        if self.weighted_model is not None:
            return self.weighted_model

        model = load_model()
        if model is None:
            raise ValueError("No weighted model file: run task_end_of_week.py or development.py to train it")

        log.info(f"[BULL] {model.bull_above:+.2f} < score < {model.bear_below:+.2f} [BEAR]")
        self.weighted_model = model
        return model

    def last_complete_bar_position(self, now: datetime | None = None) -> int:
        """Position of the newest bar that has fully closed by `now`.

        Bars are labelled by their start time. Avanza may or may not include the bar still in progress, so the
        complete bar is chosen by time, never by position: decisions only ever use fully closed candles.
        """
        is_closed = bar_index(self.bars) + BAR_DURATION <= pd.Timestamp(now or datetime.now())
        return int(np.flatnonzero(is_closed)[-1])

    @property
    def latest_price(self) -> float:
        """Most recent traded price: the bar in progress if Avanza returned it, else the last closed bar."""
        return float(self.bars["Close"].iloc[-1])

    @property
    def last_complete_close(self) -> float:
        return float(self.bars["Close"].iloc[self.last_complete_bar_position()])

    @property
    def last_complete_bar_time(self) -> datetime:
        return self.bars.index[self.last_complete_bar_position()].to_pydatetime()


class TradingFlow:
    """Decides, once per bar, whether to trade, wait, or stop trading for the day."""

    def __init__(self, market_data: MarketData) -> None:
        self.directions_sell: list[Direction] = []
        self.direction_buy: Direction | None = None
        self.direction_in_stock: Direction | None = None

        self.market_data = market_data

        self.repeated_exception_count: int = 0

    def get_action(self, portfolio: Portfolio, orders: Orders) -> FlowAction:
        self.directions_sell = []
        self.direction_buy = None

        portfolio.reload_positions(caller="get_action")
        now_time = datetime.now().time()

        if now_time <= SETTINGS.TIME.START:
            if orders.active_order or not portfolio.positions:
                return FlowAction.DO_NOTHING

            # Adopt a position held from before the start: buy() tracks it and take_profit() places its order
            held_directions = (
                direction for direction in Direction if portfolio.acquired_instrument.get(direction.value)
            )
            self.direction_buy = next(held_directions, None)
            if self.direction_buy:
                return FlowAction.TRADE

        if now_time >= min(get_trading_end_time(), SETTINGS.TIME.END):
            orders.reload_active()
            if portfolio.positions and not is_market_closed():
                self.directions_sell = [Direction.BULL, Direction.BEAR]
                return FlowAction.TRADE

            return FlowAction.EXIT_TRADING

        if self.market_data.too_old:
            self.directions_sell = [Direction.BEAR, Direction.BULL]
            return FlowAction.TRADE

        if not self.market_data.is_new:
            return FlowAction.DO_NOTHING

        self.market_data.is_new = False
        signal = self._pick_signal()
        if not signal:
            return FlowAction.DO_NOTHING

        # A time-boxed position runs until its holding time is up (Trade.stop_loss sells it then)
        if WEIGHTED_LEVELS.hold_bars and portfolio.positions:
            log.info(f"Signal {signal}{self._score_note()} ignored: the held position exits on its holding time")
            return FlowAction.DO_NOTHING

        portfolio.reload_balance()
        if portfolio.buying_power < 1100 and not portfolio.positions:
            log.info("Not enough funds on the account. No action is taken.")
            return FlowAction.EXIT_TRADING

        self.directions_sell, self.direction_buy = SIGNAL_ORDERS[signal]
        return FlowAction.TRADE

    def _pick_signal(self) -> Signal | None:
        """The weighted score's signal. With SETTINGS.LIVE_ORDERS off it is only logged as [PAPER], nothing is
        traded, and a failure is only logged."""
        if SETTINGS.LIVE_ORDERS:
            signal = self.market_data.weighted_signal()
            self._log_signal(signal, prefix="")
            return signal

        try:
            self._log_signal(self.market_data.weighted_signal(), prefix="[PAPER] ")
        except Exception as error:
            log.warning(f"[PAPER] weighted signal failed: {error}")
        return None

    def _log_signal(self, signal: Signal | None, prefix: str) -> None:
        if not signal:
            return

        latest_price = round(self.market_data.latest_price, 2)
        log.info(f"{prefix}weighted signal: {signal}{self._score_note()}. Latest price: {latest_price}")

    def _score_note(self) -> str:
        score = self.market_data.weighted_score
        return "" if score is None else f" (score {score:+.2f})"

    def wait_for_data(self):
        sleep(120 - ((datetime.now().minute * 60 + datetime.now().second) % 120) + 6)
        self.market_data.refresh()

        if not self.market_data.is_new:
            sleep(20)
            self.market_data.refresh()
            log.debug(f"Data is not new, wait and refetch. 20 seconds later data is new: {self.market_data.is_new}")

    def hit_repeated_exception(self, error: Exception) -> bool:
        if self.repeated_exception_count >= 3:
            log.warning("Repeated unknown error. Exiting trading.")
            return True

        self.repeated_exception_count += 1
        log.warning(f"Unknown error. {error}")
        return False


def _fetch_today_bars() -> pd.DataFrame | None:
    """Today's 2m bars from SETTINGS.DATA_SOURCE (Yahoo falls back to Avanza); None for an unknown source."""
    if SETTINGS.DATA_SOURCE == "yahoo":
        try:
            return Ticker().get_history(period=Period.ONE_DAY, interval=Interval.TWO_MINUTES)
        except Exception as error:
            log.warning(f"Error fetching Yahoo data: {error}. Will use avanza data instead.")
    elif SETTINGS.DATA_SOURCE != "avanza":
        return None

    return Chart.get_chart_data(TimePeriod.TODAY, Resolution.TWO_MINUTES)


def _carry_out(action: FlowAction, flow: TradingFlow, trader: Trade, market_data: MarketData) -> None:
    """Place the orders of one bar's `action`; a held position is checked for exits on bars without a trade."""
    if action == FlowAction.DO_NOTHING and flow.direction_in_stock:
        trader.stop_loss(
            flow.direction_in_stock,
            underlying_price=market_data.last_complete_close,
            bar_time=market_data.last_complete_bar_time,
        )
        return

    if action != FlowAction.TRADE:
        return

    for direction in flow.directions_sell:
        trader.sell(direction)
    trader.buy(flow.direction_buy, underlying_price=market_data.latest_price)
    trader.take_profit(flow.direction_buy, underlying_price=market_data.latest_price)
    flow.direction_in_stock = flow.direction_buy


def trade() -> None:
    log.info(
        "Start trading {} on {} | {}{}".format(
            "weighted signals" if SETTINGS.LIVE_ORDERS else "no signals (weighted on paper)",
            SETTINGS.NAME,
            SETTINGS.RESOLUTION,
            " | DRY_RUN" if DRY_RUN else "",
        ),
    )
    market_data = MarketData()
    try:
        market_data.load_weighted_model()
    except ValueError:
        if SETTINGS.LIVE_ORDERS:
            raise
        log.warning("No weighted model file yet; the weighted paper signals stay silent until one is trained")

    orders = Orders()
    orders.reload_active()

    portfolio = Portfolio()
    portfolio.reload_positions()
    portfolio.reload_balance()

    watchlists = Watchlists()
    watchlists.update_all()
    watchlists_updated_at = datetime.now()

    transactions = Transactions()

    trader = Trade(
        orders=orders,
        portfolio=portfolio,
        watchlists=watchlists,
        levels=WEIGHTED_LEVELS if SETTINGS.LIVE_ORDERS else ExitLevels(),
    )

    flow = TradingFlow(market_data)
    connection_failures = 0

    while datetime.now() < datetime.combine(datetime.today(), SETTINGS.TIME.END) + timedelta(minutes=15):
        try:
            # Exits and entries read the underlying price, so bars must be loaded before the first action
            if market_data.bars.empty:
                market_data.refresh()

            action = flow.get_action(portfolio, orders)
            if action == FlowAction.EXIT_TRADING:
                break

            _carry_out(action, flow, trader, market_data)
            if not flow.direction_in_stock and datetime.now() - watchlists_updated_at >= WATCHLIST_UPDATE_INTERVAL:
                watchlists.update_all()
                watchlists_updated_at = datetime.now()
            flow.wait_for_data()

            flow.repeated_exception_count = 0
            connection_failures = 0

        except (ConnectionError, RemoteDisconnected):
            log.warning("Connection error. Will retry")
            get_client.cache_clear()
            sleep(backoff_seconds(connection_failures, RETRY_BASE_SECONDS, RETRY_CAP_SECONDS))
            connection_failures += 1

        except Exception as error:
            if not flow.hit_repeated_exception(error):
                sleep(backoff_seconds(flow.repeated_exception_count - 1, RETRY_BASE_SECONDS, RETRY_CAP_SECONDS))
                continue

            trader.sell(Direction.BEAR)
            trader.sell(Direction.BULL)
            raise error

    transactions.log_deals(only_today=True)
    transactions.save_daily_trading_stats()
