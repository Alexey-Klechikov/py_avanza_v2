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
from services.ta.operators import get_indicators, read_top_strategies
from services.ta.strategies.models.signal import Signal
from services.ta.strategies.models.strategy import Strategy
from services.ta.strategies.signals import strategy_signal_flags
from services.trading.strategy_trigger import StrategyTrigger
from services.trading.tracked_position import ExitLevels
from tasks.fixed_rule import FIXED_RULE_LEVELS, fixed_rule_signal
from tasks.models import Direction, FlowAction
from tasks.trade import Trade
from utils.constants import TODAY_MIDNIGHT
from utils.logger.operators import get_logger

warnings.simplefilter(action="ignore", category=FutureWarning)
pd.options.mode.chained_assignment = None  # default='warn'

log = get_logger()


BAR_DURATION = pd.Timedelta(SETTINGS.RESOLUTION)

# What each signal does to the held directions: (directions to sell, direction to buy)
SIGNAL_ORDERS: dict[Signal, tuple[list[Direction], Direction | None]] = {
    Signal.LONG: ([Direction.BEAR], Direction.BULL),
    Signal.SHORT: ([Direction.BULL], Direction.BEAR),
    Signal.EXIT: ([Direction.BEAR, Direction.BULL], None),
}


class MarketData:
    """Recent 2-minute bars of the underlying, refreshed every bar, and the stored strategies evaluated on them.

    `bars` covers the last few days (the ranked strategies); `history` reaches FIXED_RULE.WARMUP_DAYS back.
    """

    def __init__(self) -> None:
        self.bars: pd.DataFrame = pd.DataFrame()
        self.history: pd.DataFrame = pd.DataFrame()
        self.is_new = False
        self.too_old = False
        self.strategies: list[Strategy] = []

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

        self.history = bars.loc[bars.index >= TODAY_MIDNIGHT - timedelta(days=SETTINGS.FIXED_RULE.WARMUP_DAYS)]
        self.bars = self.history.loc[self.history.index >= TODAY_MIDNIGHT - timedelta(days=4)]

    def load_strategies(self) -> None:
        indicators_mapping = get_indicators(self.bars)
        strategies = read_top_strategies(
            indicators_mapping,
            SETTINGS.NAME,
            filter_by_min_efficiency=SETTINGS.STRATEGY.MIN_EFFICIENCY,
            limit_count=SETTINGS.STRATEGY.COUNT_MAX,
        )
        if strategies and (not self.strategies or self.strategies[0].name != strategies[0].name):
            for strategy in strategies:
                log.info(f"Strategy rank {strategy.rank} [{strategy.efficiency}]: {strategy.name}")

        self.strategies = strategies

    def pick_signal(self, trigger: StrategyTrigger) -> Signal | None:
        """The signal of the first strategy (rank order) that signals on the last complete bar, if not ignored."""
        bar_position = self.last_complete_bar_position()
        candidates = ((strategy, self._bar_signal(strategy, bar_position)) for strategy in self.strategies)
        signal_pick = trigger.pick(candidates, now=datetime.now())
        if signal_pick is None:
            return None

        signal_summary = (
            f"Signal: {signal_pick.signal}. Strategy rank {signal_pick.strategy.rank} "
            f"[{signal_pick.strategy.efficiency}]. Latest price: {round(self.latest_price, 2)}"
        )
        if signal_pick.is_ignored:
            log.debug(f"[IGNORED] {signal_summary}")
        else:
            log.info(signal_summary)

        return signal_pick.signal

    def fixed_rule_signal(self) -> Signal | None:
        """The fixed rule's signal on the last complete bar."""
        is_closed = self.history.index + BAR_DURATION <= datetime.now()
        signal = fixed_rule_signal(self.history.loc[is_closed])
        if signal:
            mode = "" if SETTINGS.FIXED_RULE.LIVE_ORDERS else "[PAPER] "
            log.info(f"{mode}Fixed rule signal: {signal}. Latest price: {round(self.latest_price, 2)}")

        return signal

    def last_complete_bar_position(self, now: datetime | None = None) -> int:
        """Position of the newest bar that has fully closed by `now`.

        Bars are labelled by their start time. Avanza may or may not include the bar still in progress, so the
        complete bar is chosen by time, never by position: decisions only ever use fully closed candles.
        """
        is_closed = self.bars.index + BAR_DURATION <= (now or datetime.now())
        return int(np.flatnonzero(is_closed)[-1])

    def _bar_signal(self, strategy: Strategy, bar_position: int) -> Signal | None:
        signal_flags = strategy_signal_flags(self.bars, strategy)

        return Signal.from_bar(*signal_flags[bar_position])

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
        self.trigger = StrategyTrigger.from_settings()

        self.repeated_exception_count: int = 0

    def get_action(self, portfolio: Portfolio, orders: Orders) -> FlowAction:
        self.directions_sell = []
        self.direction_buy = None

        portfolio.reload_positions(caller="get_action")
        self.trigger.release_if_stale(now=datetime.now(), holds_position=bool(portfolio.positions))

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

        portfolio.reload_balance()
        if portfolio.buying_power < 1100 and not portfolio.positions:
            log.info("Not enough funds on the account. No action is taken.")
            return FlowAction.EXIT_TRADING

        self.directions_sell, self.direction_buy = SIGNAL_ORDERS[signal]
        return FlowAction.TRADE

    def _pick_signal(self) -> Signal | None:
        """The fixed rule's signal when it trades live; otherwise the ranked strategies' (the rule is only logged)."""
        if SETTINGS.FIXED_RULE.LIVE_ORDERS:
            return self.market_data.fixed_rule_signal()

        try:
            self.market_data.fixed_rule_signal()
        except Exception as e:
            log.warning(f"[PAPER] Fixed rule signal failed, ranked strategies unaffected: {e}")

        self.market_data.load_strategies()
        return self.market_data.pick_signal(self.trigger)

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
    fixed_rule_live = SETTINGS.FIXED_RULE.LIVE_ORDERS
    log.info(
        "Start trading {} on {} | {}{}".format(
            "the fixed rule" if fixed_rule_live else "ranked strategies (fixed rule on paper)",
            SETTINGS.NAME,
            SETTINGS.RESOLUTION,
            " | DRY_RUN" if DRY_RUN else "",
        ),
    )

    market_data = MarketData()

    orders = Orders()
    orders.reload_active()

    portfolio = Portfolio()
    portfolio.reload_positions()
    portfolio.reload_balance()

    watchlists = Watchlists()
    watchlists.update_all()

    transactions = Transactions()

    levels = FIXED_RULE_LEVELS if fixed_rule_live else ExitLevels()
    trade = Trade(orders=orders, portfolio=portfolio, watchlists=watchlists, levels=levels)

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
