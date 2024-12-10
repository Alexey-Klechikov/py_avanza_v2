import warnings
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from enum import Enum
from http.client import RemoteDisconnected
from time import sleep

import pandas as pd
from avanza.constants import Resolution, TimePeriod
from requests.exceptions import ConnectionError

from apis.avanza.client import get_client
from apis.avanza.operators import Chart, Orders, Portfolio, Transactions, Watchlists
from apis.avanza.trade import Trade
from apis.avanza.trade.models import Direction
from services import Storage
from services.calendar import get_market_close_time, get_market_is_close
from tasks.hold_correlation import BacklogHoldCorrelation
from tasks.hold_correlation.models import Correlation, HoldRuleCorrelation
from utils.constants import TODAY_MIDNIGHT
from utils.logger import get_logger

warnings.simplefilter(action="ignore", category=FutureWarning)
pd.options.mode.chained_assignment = None  # default='warn'

log = get_logger()


class Data:
    def __init__(self, settings):
        self.settings = settings
        self.data: pd.DataFrame = pd.DataFrame()
        self.slice_duration = 10

    def update(self) -> bool:
        storage = Storage(self.settings)
        storage.write(Chart.get_chart_data(self.settings, TimePeriod.ONE_WEEK, Resolution.TEN_MINUTES))
        try:
            data = storage.read()
        except EOFError as e:
            log.error(f"Error reading data: {e}")
            return False

        data = storage.read()

        self.data = data.loc[data.index >= TODAY_MIDNIGHT - timedelta(days=1)]

        resampled_data = self.data.resample(f"{self.slice_duration}min")
        self.data = pd.DataFrame(
            {
                "Open": resampled_data["Open"].first(),
                "Close": resampled_data["Close"].last(),
                "High": resampled_data["Close"].max(),
                "Low": resampled_data["Close"].min(),
            },
        ).dropna()

        return True


@dataclass
class Action:
    base_price: float
    latest_price: float
    price_difference: float
    multiplier: float
    efficiency: float
    direction: Direction

    @property
    def opposite_direction(self) -> Direction:
        return Direction("BULL" if self.direction == Direction.BEAR else "BEAR")


class FlowAction(Enum):
    TRADE = "TRADE"
    DO_NOTHING = "DO_NOTHING"
    EXIT_TRADING = "EXIT_TRADING"


class Flow:
    def __init__(self, settings):
        self.budget = settings.BUDGET
        self.trading_ends = min(get_market_close_time(), settings.TRADING_END)
        self.min_deciding_price_change = settings.MIN_DECIDING_PRICE_CHANGE

        self.directions_sell: list[Direction] = []
        self.directions_buy: list[Direction] = []

    def _get_action(
        self,
        hold_rules: list[HoldRuleCorrelation],
        data: Data,
    ) -> Action | None:
        if not hold_rules:
            return

        actions: list[Action] = []
        total_efficiency_coefficient = 0

        for hold_rule in hold_rules:
            deciding_interval_rows = (
                data.data.loc[
                    (
                        (data.data.index < TODAY_MIDNIGHT)
                        if hold_rule.deciding_interval.start > hold_rule.action_interval.start
                        else (data.data.index > TODAY_MIDNIGHT)
                    )
                ]
            ).between_time(hold_rule.deciding_interval.start, hold_rule.deciding_interval.end)

            if deciding_interval_rows.empty:
                continue

            deciding_interval_price_difference = (
                deciding_interval_rows["Close"].iloc[-2] - deciding_interval_rows["Open"].iloc[0]
            )

            if abs(deciding_interval_price_difference) < self.min_deciding_price_change:
                continue

            deciding_interval_direction_coefficient = (1 if hold_rule.correlation == Correlation.SAME else -1) * (
                1 if deciding_interval_price_difference > 0 else -1
            )
            total_efficiency_coefficient += deciding_interval_direction_coefficient * hold_rule.efficiency

            action_interval_rows = data.data.loc[data.data.index > TODAY_MIDNIGHT].between_time(
                hold_rule.action_interval.start,
                hold_rule.action_interval.end,
            )

            if action_interval_rows.empty:
                continue

            actions.append(
                Action(
                    base_price=action_interval_rows["Open"].iloc[0],
                    latest_price=data.data["Close"].iloc[-1],
                    price_difference=abs(round(deciding_interval_price_difference, 2)),
                    multiplier=hold_rule.multiplier,
                    efficiency=hold_rule.efficiency,
                    direction=Direction("BULL" if deciding_interval_direction_coefficient > 0 else "BEAR"),
                ),
            )

        action_direction = Direction("BULL" if total_efficiency_coefficient > 0 else "BEAR")

        actions = [i for i in actions if i.direction == action_direction]
        if not actions or round(total_efficiency_coefficient, 2) == 0:
            return

        log.info(
            f"Total efficiency coefficient: {round(total_efficiency_coefficient, 2)}. "
            + f"Signal: Signal.{'LONG' if total_efficiency_coefficient > 0 else 'SHORT'}"
            + f"Latest price: {round(data.data.iloc[-1]['Close'], 2)}",
        )

        return max(actions, key=lambda x: (x.efficiency, x.price_difference))

    def get_action(self, data: Data, backlog: BacklogHoldCorrelation, portfolio: Portfolio) -> FlowAction:
        self.directions_sell = []
        self.directions_buy = []

        sleep(600 - ((datetime.now().minute * 60 + datetime.now().second) % 600) + 6)

        portfolio.reload_positions(caller="get_action")

        # End of day
        if datetime.now().time() >= self.trading_ends:
            if not portfolio.positions or get_market_is_close():
                return FlowAction.EXIT_TRADING

            self.directions_sell = [Direction.BULL, Direction.BEAR]
            return FlowAction.TRADE

        if not data.update():
            return FlowAction.DO_NOTHING

        hold_rules = backlog.get_rules(datetime.now().time())
        action = self._get_action(hold_rules, data)

        # No action
        if action is None:
            if not portfolio.positions:
                return FlowAction.DO_NOTHING

            self.directions_sell = [Direction.BULL, Direction.BEAR]
            return FlowAction.TRADE

        # Not enough funds on the account
        portfolio.reload_balance()
        if portfolio.buying_power < self.budget and not portfolio.positions:
            log.info("Not enough funds on the account. No action is taken.")
            return FlowAction.EXIT_TRADING

        # Action
        self.directions_buy = [action.direction]
        self.directions_sell = [action.opposite_direction]
        return FlowAction.TRADE


# MAIN
def hold(dry_run: bool, settings) -> None:
    log.info("Start holding" + (" | DRY_RUN" if dry_run else ""))

    data = Data(settings)

    orders = Orders(
        account_id=settings.ACCOUNT_ID,
        filter_orderbook_name=settings.NAME,
        dry_run=dry_run,
    )

    portfolio = Portfolio(
        account_id=settings.ACCOUNT_ID,
        filter_orderbook_name=settings.NAME,
    )
    portfolio.reload_positions()
    portfolio.reload_balance()

    watchlists = Watchlists(settings, "CERTIFICATE")
    watchlists.update_all()

    backlog = BacklogHoldCorrelation()
    backlog.read_rules(settings)

    trade = Trade(
        orders=orders,
        portfolio=portfolio,
        watchlists=watchlists,
        dry_run=dry_run,
        budget_percent=settings.BUDGET,
        take_profit_percent=settings.TRADING_TAKE_PROFIT,
    )

    flow = Flow(settings)

    while datetime.now().time() < time(17, 15):
        try:
            action = flow.get_action(data, backlog, portfolio)
        except (ConnectionError, RemoteDisconnected):
            get_client.cache_clear()

        if action == FlowAction.DO_NOTHING:
            continue

        elif action == FlowAction.EXIT_TRADING:
            break

        elif action == FlowAction.TRADE:
            for direction in flow.directions_sell:
                trade.sell(direction)

            for direction in flow.directions_buy:
                trade.buy(direction)
                trade.take_profit(direction)

    Transactions(settings.ACCOUNT_ID).log_deals(only_today=True)
