import warnings
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
from services.calendar.operators import get_market_close_time, market_is_close
from services.storage.operators import Storage
from services.ta.strategies.models.signal import Signal
from services.trading.tracked_position import ExitLevels
from tasks.backtest.bars import bar_index
from tasks.backtest.model import WEIGHTED_LEVELS, WeightedModel, load_model, weighted_signal
from tasks.fixed_rule import FIXED_RULE_LEVELS, fixed_rule_signal
from tasks.trade.models import Direction, FlowAction, SignalSource
from tasks.trade.states import Trade
from utils.constants import TODAY_MIDNIGHT
from utils.logger.operators import get_logger

warnings.simplefilter(action="ignore", category=FutureWarning)
pd.options.mode.chained_assignment = None  # default='warn'

log = get_logger()


BAR_DURATION = pd.Timedelta(SETTINGS.RESOLUTION)

HISTORY_DAYS = max(SETTINGS.FIXED_RULE.WARMUP_DAYS, SETTINGS.WEIGHTED_SCORE.WARMUP_DAYS)
# Exit levels per live source; with no live source (None) nothing is bought, and held positions only exit at the end
SOURCE_LEVELS: dict[SignalSource | None, ExitLevels] = {
    None: ExitLevels(),
    SignalSource.FIXED_RULE: FIXED_RULE_LEVELS,
    SignalSource.WEIGHTED: WEIGHTED_LEVELS,
}


def _live_source() -> SignalSource | None:
    return None if SETTINGS.LIVE_SIGNAL_SOURCE is None else SignalSource(SETTINGS.LIVE_SIGNAL_SOURCE)


# What each signal does to the held directions: (directions to sell, direction to buy)
SIGNAL_ORDERS: dict[Signal, tuple[list[Direction], Direction | None]] = {
    Signal.LONG: ([Direction.BEAR], Direction.BULL),
    Signal.SHORT: ([Direction.BULL], Direction.BEAR),
    Signal.EXIT: ([Direction.BEAR, Direction.BULL], None),
}


class MarketData:
    """Recent 2-minute bars of the underlying, refreshed every bar, and the signal sources evaluated on them.

    `bars` covers the last few days (prices for orders and exits); `history` reaches HISTORY_DAYS back (fixed rule
    and weighted score), which also use the 1d cache (`daily`, refreshed only at end of day) and the weighted model.
    """

    def __init__(self) -> None:
        self.bars: pd.DataFrame = pd.DataFrame()
        self.history: pd.DataFrame = pd.DataFrame()
        self.daily: pd.DataFrame = pd.DataFrame()
        self.weighted_model: WeightedModel | None = None
        self.is_new = False
        self.too_old = False

    def refresh(self) -> None:
        storage = Storage()

        bars = storage.read()

        if ((datetime.now() - bars.index[-1]).seconds) < 2 * 60:  # type: ignore
            self.too_old = False
            self.is_new = True

        else:
            new_bars = None
            data_source = SETTINGS.DATA_SOURCE
            if data_source == "yahoo":
                try:
                    new_bars = Ticker().get_history(period=Period.ONE_DAY, interval=Interval.TWO_MINUTES)
                except Exception as e:
                    log.warning(f"Error fetching Yahoo data: {e}. Will use avanza data instead.")
                    data_source = "avanza"

            if data_source == "avanza":
                new_bars = Chart.get_chart_data(TimePeriod.TODAY, Resolution.TWO_MINUTES)

            if new_bars is None:
                raise ValueError("No data fetched")

            storage.write(new_bars)

            bars_count_before = bars.shape[0]
            bars = storage.read()

            self.too_old = ((datetime.now() - bars.index[-1]).seconds // 60) > 15
            self.is_new = bars_count_before != bars.shape[0]

        self.history = bars.loc[bars.index >= TODAY_MIDNIGHT - timedelta(days=HISTORY_DAYS)]
        self.bars = self.history.loc[self.history.index >= TODAY_MIDNIGHT - timedelta(days=4)]

    def source_signal(self, source: SignalSource) -> Signal | None:
        """The fixed rule's or the weighted score's signal on the last complete bar."""
        closed_history = self.history.loc[bar_index(self.history) + BAR_DURATION <= pd.Timestamp.now()]
        if source == SignalSource.FIXED_RULE:
            return fixed_rule_signal(closed_history)

        if self.daily.empty:
            self.daily = Storage(resolution="1d").read()
        if self.weighted_model is None:
            self.weighted_model = load_model()
        if self.weighted_model is None:
            raise ValueError("No weighted model file: run task_end_of_week.py or development.py to train it")

        return weighted_signal(self.weighted_model, closed_history, self.daily)

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

        # Start of the day
        if datetime.now().time() <= SETTINGS.TIME.START:
            if orders.active_order or not portfolio.positions:
                return FlowAction.DO_NOTHING

            for direction in [Direction.BULL, Direction.BEAR]:
                if not portfolio.acquired_instrument.get(direction.value):
                    continue

                self.direction_buy = direction
                return FlowAction.TRADE

        # End of day
        if datetime.now().time() >= min(get_market_close_time(), SETTINGS.TIME.END):
            orders.reload_active()
            if portfolio.positions and not market_is_close():
                self.directions_sell = [Direction.BULL, Direction.BEAR]
                return FlowAction.TRADE

            return FlowAction.EXIT_TRADING

        # No new data
        if self.market_data.too_old:
            self.directions_sell = [Direction.BEAR, Direction.BULL]
            return FlowAction.TRADE

        if not self.market_data.is_new:
            return FlowAction.DO_NOTHING

        # Trade
        self.market_data.is_new = False
        signal = self._pick_signal()
        if not signal:
            return FlowAction.DO_NOTHING

        # A time-boxed position runs until its holding time is up (Trade.stop_loss sells it then)
        if SOURCE_LEVELS[_live_source()].hold_bars and portfolio.positions:
            log.info(f"Signal {signal} ignored: the held position exits on its holding time")
            return FlowAction.DO_NOTHING

        portfolio.reload_balance()
        if portfolio.buying_power < 1100 and not portfolio.positions:
            log.info("Not enough funds on the account. No action is taken.")
            return FlowAction.EXIT_TRADING

        self.directions_sell, self.direction_buy = SIGNAL_ORDERS[signal]
        return FlowAction.TRADE

    def _pick_signal(self) -> Signal | None:
        """The live source's signal (SETTINGS.LIVE_SIGNAL_SOURCE; None trades nothing). The other sources are only
        logged as [PAPER], and a failure there never reaches the live source."""
        live_source = _live_source()
        for source in SignalSource:
            if source == live_source:
                continue
            try:
                self._log_source_signal(source, self.market_data.source_signal(source), prefix="[PAPER] ")
            except Exception as e:
                log.warning(f"[PAPER] {source.value} signal failed, live source unaffected: {e}")

        if live_source is None:
            return None

        signal = self.market_data.source_signal(live_source)
        self._log_source_signal(live_source, signal, prefix="")
        return signal

    def _log_source_signal(self, source: SignalSource, signal: Signal | None, prefix: str) -> None:
        if signal:
            log.info(
                f"{prefix}{source.value} signal: {signal}. Latest price: {round(self.market_data.latest_price, 2)}",
            )

    def wait_for_data(self):
        sleep(120 - ((datetime.now().minute * 60 + datetime.now().second) % 120) + 6)
        self.market_data.refresh()

        if not self.market_data.is_new:
            sleep(20)
            self.market_data.refresh()
            log.debug(f"Data is not new, wait and refetch. 20 seconds later data is new: {self.market_data.is_new}")

    def hit_repeated_exception(self, e: Exception) -> bool:
        if self.repeated_exception_count >= 3:
            log.warning("Repeated unknown error. Exiting trading.")
            return True

        self.repeated_exception_count += 1
        log.warning(f"Unknown error. {e}")
        return False


# MAIN
def trade() -> None:
    live_source = _live_source()
    log.info(
        "Start trading {} signals on {} | {}{}".format(
            live_source.value if live_source else "no (all sources on paper)",
            SETTINGS.NAME,
            SETTINGS.RESOLUTION,
            " | DRY_RUN" if DRY_RUN else "",
        ),
    )
    if live_source == SignalSource.WEIGHTED and load_model() is None:
        raise ValueError("LIVE_SIGNAL_SOURCE is weighted but there is no weighted model file to trade")

    market_data = MarketData()

    orders = Orders()
    orders.reload_active()

    portfolio = Portfolio()
    portfolio.reload_positions()
    portfolio.reload_balance()

    watchlists = Watchlists()
    watchlists.update_all()

    transactions = Transactions()

    trade = Trade(orders=orders, portfolio=portfolio, watchlists=watchlists, levels=SOURCE_LEVELS[live_source])

    flow = TradingFlow(market_data)

    while datetime.now() < datetime.combine(datetime.today(), SETTINGS.TIME.END) + timedelta(minutes=15):
        try:
            # Exits and entries read the underlying price, so bars must be loaded before the first action
            if market_data.bars.empty:
                market_data.refresh()

            action = flow.get_action(portfolio, orders)

            if action == FlowAction.DO_NOTHING and flow.direction_in_stock:
                trade.stop_loss(
                    flow.direction_in_stock,
                    underlying_price=market_data.last_complete_close,
                    bar_time=market_data.last_complete_bar_time,
                )

            elif action == FlowAction.TRADE:
                [trade.sell(direction) for direction in flow.directions_sell]
                trade.buy(flow.direction_buy, underlying_price=market_data.latest_price)
                trade.take_profit(flow.direction_buy, underlying_price=market_data.latest_price)
                flow.direction_in_stock = flow.direction_buy

            elif action == FlowAction.EXIT_TRADING:
                break

            flow.wait_for_data()

            flow.repeated_exception_count = 0

        except (ConnectionError, RemoteDisconnected):
            log.warning("Connection error. Will retry")
            get_client.cache_clear()

        except Exception as e:
            if not flow.hit_repeated_exception(e):
                continue

            [trade.sell(direction) for direction in (Direction.BEAR, Direction.BULL)]
            raise e

    transactions.log_deals(only_today=True)
    transactions.save_daily_trading_stats()
