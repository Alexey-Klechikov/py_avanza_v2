from unittest import TestCase

from config import SETTINGS
from services.trading.tracked_position import ExitLevels, TrackedPosition

ENTRY_PRICE = 1000.0
# Price-based exits on, as a source like the fixed rule sets them
TAKE_PROFIT, STOP_LOSS, PULLBACK_TRIGGER = 0.045, 0.03, 0.0225
LEVELS = ExitLevels(take_profit=TAKE_PROFIT, stop_loss=STOP_LOSS, pullback_trigger=PULLBACK_TRIGGER)


def _take_profit(position: TrackedPosition) -> float:
    assert position.take_profit_price is not None
    return position.take_profit_price


def _stop_loss(position: TrackedPosition) -> float:
    assert position.stop_loss_price is not None
    return position.stop_loss_price


def _underlying_price_after(move_in_settings_units: float) -> float:
    """Underlying price after a move expressed like the settings (instrument %, before leverage)."""
    return ENTRY_PRICE * (1 + move_in_settings_units / SETTINGS.MULTIPLIER)


class Test_TrackedPosition(TestCase):
    def test_levels_mirror_for_short(self):
        long_position = TrackedPosition.open(is_long=True, entry_price=ENTRY_PRICE, levels=LEVELS)
        short_position = TrackedPosition.open(is_long=False, entry_price=ENTRY_PRICE, levels=LEVELS)

        assert _take_profit(long_position) > ENTRY_PRICE > _stop_loss(long_position)
        assert _take_profit(short_position) < ENTRY_PRICE < _stop_loss(short_position)

    def test_flat_exit_loses_the_spread(self):
        for is_long in (True, False):
            position = TrackedPosition.open(is_long=is_long, entry_price=ENTRY_PRICE, levels=LEVELS)

            assert abs(position.capital_return(ENTRY_PRICE) + SETTINGS.SPREAD_DEFAULT) < 1e-12
            assert (
                abs(position.profit(ENTRY_PRICE) + SETTINGS.SPREAD_DEFAULT * ENTRY_PRICE / SETTINGS.MULTIPLIER) < 1e-9
            )

    def test_spread_is_taken_from_the_sale_proceeds(self):
        for is_long in (True, False):
            position = TrackedPosition.open(is_long=is_long, entry_price=ENTRY_PRICE, levels=LEVELS)
            gross = 0.045  # instrument up 4.5% before costs
            sell_price = ENTRY_PRICE * (1 + (1 if is_long else -1) * gross / SETTINGS.MULTIPLIER)

            expected = (1 + gross) * (1 - SETTINGS.SPREAD_DEFAULT) - 1
            assert abs(position.capital_return(sell_price) - expected) < 1e-12

    def test_take_profit_fills_inside_bar_or_at_gap_open(self):
        position = TrackedPosition.open(is_long=True, entry_price=ENTRY_PRICE, levels=LEVELS)

        assert not position.hit_take_profit(high=_take_profit(position) - 0.01, low=ENTRY_PRICE)
        assert position.hit_take_profit(high=_take_profit(position), low=ENTRY_PRICE)
        assert position.take_profit_fill(open_price=ENTRY_PRICE) == _take_profit(position)
        assert position.take_profit_fill(open_price=_take_profit(position) + 5) == _take_profit(position) + 5

    def test_instrument_take_profit_scales_with_actual_leverage(self):
        nominal = TrackedPosition.open(is_long=False, entry_price=ENTRY_PRICE, levels=LEVELS)
        higher_leverage = TrackedPosition.open(
            is_long=False,
            entry_price=ENTRY_PRICE,
            instrument_leverage=2 * SETTINGS.MULTIPLIER,
            levels=LEVELS,
        )
        nominal_limit = nominal.instrument_take_profit_price(100.0)
        higher_leverage_limit = higher_leverage.instrument_take_profit_price(100.0)

        assert nominal_limit is not None and abs(nominal_limit - 100.0 * (1 + TAKE_PROFIT)) < 1e-9
        assert higher_leverage_limit is not None and abs(higher_leverage_limit - 100.0 * (1 + 2 * TAKE_PROFIT)) < 1e-9

    def test_missing_leverage_falls_back_to_nominal(self):
        assert TrackedPosition.open(
            is_long=True,
            entry_price=ENTRY_PRICE,
            instrument_leverage=0,
        ).instrument_leverage == (SETTINGS.MULTIPLIER)

    def test_stop_loss_needs_consecutive_confirmations(self):
        position = TrackedPosition.open(is_long=True, entry_price=ENTRY_PRICE, levels=LEVELS)
        below_stop = _stop_loss(position) - 1

        for _ in range(SETTINGS.STOP_LOSS.CONFIRMATION_COUNT):
            assert not position.confirm_stop_loss(below_stop)

        assert not position.confirm_stop_loss(ENTRY_PRICE)  # recovery resets the count
        for _ in range(SETTINGS.STOP_LOSS.CONFIRMATION_COUNT):
            assert not position.confirm_stop_loss(below_stop)
        assert position.confirm_stop_loss(below_stop)

    def test_pullback_after_trigger_profit(self):
        position = TrackedPosition.open(is_long=True, entry_price=ENTRY_PRICE, levels=LEVELS)

        assert not position.confirm_pullback(_underlying_price_after(2 * PULLBACK_TRIGGER))
        attempts = SETTINGS.PULLBACK.CONFIRMATION_COUNT + 1
        confirmations = [position.confirm_pullback(ENTRY_PRICE * 0.999) for _ in range(attempts)]
        assert confirmations[-1] and not any(confirmations[:-1])

    def test_custom_levels(self):
        levels = ExitLevels(take_profit=0.07, stop_loss=0.12, pullback_trigger=0.035)
        position = TrackedPosition.open(is_long=False, entry_price=ENTRY_PRICE, levels=levels)

        assert _take_profit(position) == ENTRY_PRICE * (1 - 0.07 / SETTINGS.MULTIPLIER)
        assert _stop_loss(position) == ENTRY_PRICE * (1 + 0.12 / SETTINGS.MULTIPLIER)
        assert position.pullback_trigger == 0.035

    def test_time_boxed_position_without_price_levels(self):
        levels = ExitLevels(take_profit=None, stop_loss=None, pullback_trigger=None, hold_bars=3)
        position = TrackedPosition.open(is_long=True, entry_price=ENTRY_PRICE, levels=levels)

        assert not position.hit_take_profit(high=2 * ENTRY_PRICE, low=0)
        assert position.instrument_take_profit_price(10.0) is None
        assert not position.confirm_stop_loss(0.5 * ENTRY_PRICE)
        assert not position.confirm_pullback(1.5 * ENTRY_PRICE)
        assert [position.confirm_hold_expiry() for _ in range(3)] == [False, False, True]

    def test_default_levels_never_exit(self):
        position = TrackedPosition.open(is_long=True, entry_price=ENTRY_PRICE)

        assert not position.hit_take_profit(high=2 * ENTRY_PRICE, low=0)
        assert not position.confirm_stop_loss(0.5 * ENTRY_PRICE)

        assert not any(position.confirm_hold_expiry() for _ in range(500))
