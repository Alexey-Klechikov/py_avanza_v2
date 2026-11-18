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
    def _pick(self, live_source: str | None, failing_source: str | None = None):
        from dataclasses import replace
        from unittest.mock import MagicMock, patch

        from config import SETTINGS
        from services.ta.strategies.models.signal import Signal
        from tasks.trade import main

        source_signals = {"fixed_rule": Signal.SHORT, "weighted": Signal.EXIT}

        def source_signal(source):
            if source.value == failing_source:
                raise ValueError("no model")
            return source_signals[source.value]

        market_data = MagicMock(weighted_score=None)
        market_data.source_signal.side_effect = source_signal
        with patch.object(main, "SETTINGS", replace(SETTINGS, LIVE_SIGNAL_SOURCE=live_source)):
            signal = main.TradingFlow(market_data)._pick_signal()

        called = [call.args[0].value for call in market_data.source_signal.call_args_list]
        return signal, market_data, called, Signal

    def test_no_live_source_trades_nothing_and_logs_every_source(self):
        signal, _, called, _ = self._pick(None)

        assert signal is None
        assert sorted(called) == ["fixed_rule", "weighted"]

    def test_weighted_live_source(self):
        signal, _, called, Signal = self._pick("weighted")

        assert signal == Signal.EXIT
        assert called == ["fixed_rule", "weighted"]

    def test_paper_failure_does_not_reach_the_live_source(self):
        signal, _, _, Signal = self._pick("fixed_rule", failing_source="weighted")

        assert signal == Signal.SHORT


class Test_TimeBoxedFlow(TestCase):
    def test_signal_ignored_while_a_time_boxed_position_is_held(self):
        from dataclasses import replace
        from unittest.mock import MagicMock, patch

        from config import SETTINGS
        from services.ta.strategies.models.signal import Signal
        from tasks.trade import main

        market_data = MagicMock(is_new=True, too_old=False, weighted_score=4.2)
        market_data.source_signal.return_value = Signal.SHORT
        portfolio = MagicMock(positions=["held"], buying_power=10_000)
        flow = main.TradingFlow(market_data)
        with (
            patch.object(main, "SETTINGS", replace(SETTINGS, LIVE_SIGNAL_SOURCE="weighted")),
            patch.object(main, "datetime", MagicMock(now=lambda: datetime(2026, 11, 18, 12, 0))),
            patch.object(main, "get_market_close_time", return_value=SETTINGS.TIME.END),
        ):
            action = flow.get_action(portfolio, orders=MagicMock())

        assert action == main.FlowAction.DO_NOTHING


class Test_ScoreLogging(TestCase):
    def test_range_logged_once_and_score_on_signals(self):
        from datetime import date
        from unittest.mock import patch

        from services.ta.strategies.models.signal import Signal
        from tasks.backtest.model import WeightedModel
        from tasks.trade import main
        from tasks.trade.models import SignalSource

        model = WeightedModel(
            weights={"a": 1.0},
            intercept=0.0,
            center=0.5,
            entry_threshold=13.0,
            exit_threshold=0.0,
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
            main.TradingFlow(market_data)._log_source_signal(SignalSource.WEIGHTED, Signal.LONG, prefix="[PAPER] ")

        messages = [call.args[0] for call in info.call_args_list]
        assert messages[0] == "[BULL] +13.50 < score < -12.50 [BEAR]"
        assert len(messages) == 2 and "(score +14.20)" in messages[1]
