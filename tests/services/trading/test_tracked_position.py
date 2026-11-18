from unittest import TestCase

from src.config import SETTINGS
from src.services.trading.tracked_position import ExitLevels, TrackedPosition

ENTRY_PRICE = 1000.0


def _underlying_price_after(move_in_settings_units: float) -> float:
    """Underlying price after a move expressed like the settings (instrument %, before leverage)."""
    return ENTRY_PRICE * (1 + move_in_settings_units / SETTINGS.MULTIPLIER)


class Test_TrackedPosition(TestCase):
    def test_levels_mirror_for_short(self):
        long_position = TrackedPosition.open(is_long=True, entry_price=ENTRY_PRICE)
        short_position = TrackedPosition.open(is_long=False, entry_price=ENTRY_PRICE)

        assert long_position.take_profit_price > ENTRY_PRICE > long_position.stop_loss_price
        assert short_position.take_profit_price < ENTRY_PRICE < short_position.stop_loss_price

    def test_flat_exit_loses_the_spread(self):
        for is_long in (True, False):
            position = TrackedPosition.open(is_long=is_long, entry_price=ENTRY_PRICE)

            assert abs(position.capital_return(ENTRY_PRICE) + SETTINGS.SPREAD_DEFAULT) < 1e-12
            assert (
                abs(position.profit(ENTRY_PRICE) + SETTINGS.SPREAD_DEFAULT * ENTRY_PRICE / SETTINGS.MULTIPLIER) < 1e-9
            )

    def test_spread_is_taken_from_the_sale_proceeds(self):
        for is_long in (True, False):
            position = TrackedPosition.open(is_long=is_long, entry_price=ENTRY_PRICE)
            gross = 0.045  # instrument up 4.5% before costs
            sell_price = ENTRY_PRICE * (1 + (1 if is_long else -1) * gross / SETTINGS.MULTIPLIER)

            expected = (1 + gross) * (1 - SETTINGS.SPREAD_DEFAULT) - 1
            assert abs(position.capital_return(sell_price) - expected) < 1e-12

    def test_take_profit_fills_inside_bar_or_at_gap_open(self):
        position = TrackedPosition.open(is_long=True, entry_price=ENTRY_PRICE)

        assert not position.hit_take_profit(high=position.take_profit_price - 0.01, low=ENTRY_PRICE)
        assert position.hit_take_profit(high=position.take_profit_price, low=ENTRY_PRICE)
        assert position.take_profit_fill(open_price=ENTRY_PRICE) == position.take_profit_price
        assert position.take_profit_fill(open_price=position.take_profit_price + 5) == position.take_profit_price + 5

    def test_instrument_take_profit_scales_with_actual_leverage(self):
        nominal = TrackedPosition.open(is_long=False, entry_price=ENTRY_PRICE)
        higher_leverage = TrackedPosition.open(
            is_long=False,
            entry_price=ENTRY_PRICE,
            instrument_leverage=2 * SETTINGS.MULTIPLIER,
        )

        assert abs(nominal.instrument_take_profit_price(100.0) - 100.0 * (1 + SETTINGS.TAKE_PROFIT.VALUE)) < 1e-9
        assert (
            abs(higher_leverage.instrument_take_profit_price(100.0) - 100.0 * (1 + 2 * SETTINGS.TAKE_PROFIT.VALUE))
            < 1e-9
        )

    def test_missing_leverage_falls_back_to_nominal(self):
        assert TrackedPosition.open(
            is_long=True,
            entry_price=ENTRY_PRICE,
            instrument_leverage=0,
        ).instrument_leverage == (SETTINGS.MULTIPLIER)

    def test_stop_loss_needs_consecutive_confirmations(self):
        position = TrackedPosition.open(is_long=True, entry_price=ENTRY_PRICE)
        below_stop = position.stop_loss_price - 1

        for _ in range(SETTINGS.STOP_LOSS.CONFIRMATION_COUNT):
            assert not position.confirm_stop_loss(below_stop)

        assert not position.confirm_stop_loss(ENTRY_PRICE)  # recovery resets the count
        for _ in range(SETTINGS.STOP_LOSS.CONFIRMATION_COUNT):
            assert not position.confirm_stop_loss(below_stop)
        assert position.confirm_stop_loss(below_stop)

    def test_pullback_after_trigger_profit(self):
        position = TrackedPosition.open(is_long=True, entry_price=ENTRY_PRICE)

        assert not position.confirm_pullback(_underlying_price_after(2 * SETTINGS.PULLBACK.TRIGGER_PROFIT))
        attempts = SETTINGS.PULLBACK.CONFIRMATION_COUNT + 1
        confirmations = [position.confirm_pullback(ENTRY_PRICE * 0.999) for _ in range(attempts)]
        assert confirmations[-1] and not any(confirmations[:-1])

    def test_custom_levels(self):
        levels = ExitLevels(take_profit=0.07, stop_loss=0.12, pullback_trigger=0.035)
        position = TrackedPosition.open(is_long=False, entry_price=ENTRY_PRICE, levels=levels)

        assert position.take_profit_price == ENTRY_PRICE * (1 - 0.07 / SETTINGS.MULTIPLIER)
        assert position.stop_loss_price == ENTRY_PRICE * (1 + 0.12 / SETTINGS.MULTIPLIER)
        assert position.pullback_trigger == 0.035
