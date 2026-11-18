from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, patch

from services.trading.tracked_position import ExitLevels
from tasks.trade import states
from tasks.trade.models import Direction

HOLD = ExitLevels(take_profit=None, stop_loss=None, pullback_trigger=None, hold_bars=2)


def _trade() -> tuple[states.Trade, MagicMock]:
    """A Trade holding a BULL position, and its orders mock."""
    held = SimpleNamespace(
        acquired_price=10.0,
        volume=100,
        instrument=SimpleNamespace(id="1", name="BULL OMX X10", type=SimpleNamespace(name="CERTIFICATE")),
        quote=SimpleNamespace(buy=10.0),
    )
    portfolio = MagicMock(acquired_instrument={"BULL": held})
    orders = MagicMock()
    return states.Trade(orders=orders, portfolio=portfolio, watchlists=MagicMock(), levels=HOLD), orders


class Test_TradeHoldingTime(TestCase):
    def test_sells_once_the_holding_time_is_up(self):
        trade, orders = _trade()
        bar = datetime(2026, 11, 18, 12, 0)
        with (
            patch.object(states, "DRY_RUN", False),
            patch.object(states, "Instrument", return_value=MagicMock(get_buy_price=MagicMock(return_value=10.1))),
        ):
            trade.stop_loss(Direction.BULL, underlying_price=1000, bar_time=bar)
            orders.place.assert_not_called()

            trade.stop_loss(Direction.BULL, underlying_price=1000, bar_time=bar)  # same bar: not counted again
            orders.place.assert_not_called()

            trade.stop_loss(Direction.BULL, underlying_price=1000, bar_time=bar + timedelta(minutes=2))

        assert orders.place.call_args.kwargs["price"] == 10.1

    def test_no_take_profit_order_without_a_level(self):
        trade, orders = _trade()
        with patch.object(states, "DRY_RUN", False):
            trade.take_profit(Direction.BULL, underlying_price=1000)

        orders.place.assert_not_called()
