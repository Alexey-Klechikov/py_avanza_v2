from datetime import datetime
from unittest import TestCase

import pandas as pd

from src.tasks.main import MarketData


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
    def _flow(self, live_orders: bool):
        from dataclasses import replace
        from unittest.mock import MagicMock, patch

        from src.config import SETTINGS
        from src.services.ta.strategies.models.signal import Signal
        from src.tasks import main

        market_data = MagicMock()
        market_data.fixed_rule_signal.return_value = Signal.SHORT
        market_data.pick_signal.return_value = Signal.LONG
        settings = replace(SETTINGS, FIXED_RULE=replace(SETTINGS.FIXED_RULE, LIVE_ORDERS=live_orders))
        with patch.object(main, "SETTINGS", settings):
            return main.TradingFlow(market_data)._pick_signal(), market_data, Signal

    def test_live_fixed_rule_replaces_ranked_strategies(self):
        signal, market_data, Signal = self._flow(live_orders=True)

        assert signal == Signal.SHORT
        market_data.load_strategies.assert_not_called()

    def test_paper_fixed_rule_keeps_ranked_strategies(self):
        signal, market_data, Signal = self._flow(live_orders=False)

        assert signal == Signal.LONG
        market_data.fixed_rule_signal.assert_called_once()
