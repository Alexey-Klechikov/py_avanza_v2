from datetime import datetime
from unittest import TestCase

import pandas as pd

from tasks.trade.main import MarketData


def _market_data(last_bar_start: str, bars: int = 5) -> MarketData:
    market_data = MarketData()
    index = pd.date_range(end=last_bar_start, periods=bars, freq="2min")
    market_data.bars = pd.DataFrame({"Close": [float(number) for number in range(bars)]}, index=index)
    return market_data


class Test_LastCompleteBar(TestCase):
    def test_skips_the_candle_in_progress(self):
        market_data = _market_data(last_bar_start="2026-11-17 10:00")  # Avanza returned the 10:00 candle

        position = market_data.last_complete_bar_position(now=datetime(2026, 11, 17, 10, 0, 6))

        assert market_data.bars.index[position] == pd.Timestamp("2026-11-17 09:58")

    def test_uses_the_last_candle_when_no_candle_is_in_progress(self):
        market_data = _market_data(last_bar_start="2026-11-17 09:58")  # Avanza left the 10:00 candle out

        position = market_data.last_complete_bar_position(now=datetime(2026, 11, 17, 10, 0, 6))

        assert market_data.bars.index[position] == pd.Timestamp("2026-11-17 09:58")


class Test_PickSignal(TestCase):
    def _pick(self, live_orders: bool, fails: bool = False):
        from dataclasses import replace
        from unittest.mock import MagicMock, patch

        from config import SETTINGS
        from services.ta.strategies.models.signal import Signal
        from tasks.trade import main

        market_data = MagicMock(weighted_score=None)
        market_data.weighted_signal.side_effect = ValueError("no model") if fails else None
        market_data.weighted_signal.return_value = Signal.SHORT
        with patch.object(main, "SETTINGS", replace(SETTINGS, LIVE_ORDERS=live_orders)):
            signal = main.TradingFlow(market_data)._pick_signal()

        return signal, market_data, Signal

    def test_paper_mode_trades_nothing_but_evaluates_the_signal(self):
        signal, market_data, _ = self._pick(live_orders=False)

        assert signal is None
        market_data.weighted_signal.assert_called_once()

    def test_live_orders_trade_the_weighted_signal(self):
        signal, _, Signal = self._pick(live_orders=True)

        assert signal == Signal.SHORT

    def test_paper_mode_failure_is_only_logged(self):
        signal, _, _ = self._pick(live_orders=False, fails=True)

        assert signal is None

    def test_live_orders_failure_propagates(self):
        with self.assertRaises(ValueError):
            self._pick(live_orders=True, fails=True)


class Test_TimeBoxedFlow(TestCase):
    def test_signal_ignored_while_a_time_boxed_position_is_held(self):
        from dataclasses import replace
        from unittest.mock import MagicMock, patch

        from config import SETTINGS
        from services.ta.strategies.models.signal import Signal
        from tasks.trade import main

        market_data = MagicMock(is_new=True, too_old=False, weighted_score=4.2)
        market_data.weighted_signal.return_value = Signal.SHORT
        portfolio = MagicMock(positions=["held"], buying_power=10_000)
        flow = main.TradingFlow(market_data)
        with (
            patch.object(main, "SETTINGS", replace(SETTINGS, LIVE_ORDERS=True)),
            patch.object(main, "datetime", MagicMock(now=lambda: datetime(2026, 11, 18, 12, 0))),
            patch.object(main, "get_trading_end_time", return_value=SETTINGS.TIME.END),
        ):
            action = flow.get_action(portfolio, orders=MagicMock())

        assert action == main.FlowAction.DO_NOTHING


class Test_ScoreLogging(TestCase):
    def test_range_logged_once_and_score_on_signals(self):
        from datetime import date
        from unittest.mock import patch

        from services.ta.strategies.models.signal import Signal
        from tasks.shared.weighted_model import WeightedModel
        from tasks.trade import main

        model = WeightedModel(
            weights={"a": 1.0},
            intercept=0.0,
            center=0.5,
            entry_threshold=13.0,
            horizon_bars=60,
            alpha=0.1,
            trained_from=date(2026, 1, 1),
            trained_to=date(2026, 1, 2),
        )
        market_data = main.MarketData()
        with patch.object(main, "load_model", return_value=model), patch.object(main.log, "info") as info:
            market_data.load_weighted_model()
            market_data.load_weighted_model()

            market_data.weighted_score = 14.2
            market_data.bars = pd.DataFrame({"Close": [100.0]})
            main.TradingFlow(market_data)._log_signal(Signal.LONG, prefix="[PAPER] ")

        messages = [call.args[0] for call in info.call_args_list]
        assert messages[0] == "[BULL] +13.50 < score < -12.50 [BEAR]"
        assert len(messages) == 2 and "(score +14.20)" in messages[1]


class Test_StartOfDay(TestCase):
    def _action(self, held: dict, active_order=None):
        from unittest.mock import MagicMock, patch

        from config import SETTINGS
        from tasks.trade import main

        portfolio = MagicMock(positions=list(held.values()), acquired_instrument=held)
        flow = main.TradingFlow(MagicMock(too_old=False, is_new=False))
        before_start = datetime.combine(datetime(2026, 11, 18), SETTINGS.TIME.START).replace(minute=0)
        with (
            patch.object(main, "datetime", MagicMock(now=lambda: before_start)),
            patch.object(main, "get_trading_end_time", return_value=SETTINGS.TIME.END),
        ):
            action = flow.get_action(portfolio, orders=MagicMock(active_order=active_order))

        return action, flow, main

    def test_adopts_a_position_held_before_the_start(self):
        action, flow, main = self._action(held={"BEAR": "held"})

        assert action == main.FlowAction.TRADE and flow.direction_buy == main.Direction.BEAR

    def test_waits_while_an_order_is_active(self):
        action, flow, main = self._action(held={"BULL": "held"}, active_order="order")

        assert action == main.FlowAction.DO_NOTHING and flow.direction_buy is None
