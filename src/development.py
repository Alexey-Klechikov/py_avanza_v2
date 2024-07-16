import warnings
from datetime import datetime, timedelta
from typing import List, Tuple

from data.settings import OMX30_YAHOO
from operators import backtest
from services.storage import Storage
from services.ta.strategies.models import ComposeStrategiesListMethod
from utils.logger import get_logger, set_handlers

warnings.simplefilter(action="ignore", category=FutureWarning)


set_handlers("development")
log = get_logger()


def run_full_strategies_generation(indicators_selector: List[Tuple[str, str]]):
    resolution = "5m"
    period_days = 60

    data = Storage(OMX30_YAHOO, resolution=resolution).read()
    data = data.loc[
        data.index >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=period_days)
    ]

    log.warning("Generating strategies")
    backtest(
        data,
        indicators_selector,
        ComposeStrategiesListMethod.GENERATE,
        old_strategies_file_name=None,
        new_strategies_file_name="dev_strategies_3_indicators.json",
        indicators_filter=[],
        plot=False,
    )

    log.warning("Extending strategies (3 -> 4)")
    backtest(
        data,
        indicators_selector,
        ComposeStrategiesListMethod.EXTEND,
        old_strategies_file_name="dev_strategies_3_indicators.json",
        new_strategies_file_name="dev_strategies_4_indicators.json",
        indicators_filter=[],
        plot=False,
    )

    log.warning("Extending strategies (4 -> 5)")
    backtest(
        data,
        indicators_selector,
        ComposeStrategiesListMethod.EXTEND,
        old_strategies_file_name="dev_strategies_4_indicators.json",
        new_strategies_file_name="dev_strategies_5_indicators.json",
        indicators_filter=[],
        plot=False,
    )

    log.warning("Saving strategies")
    backtest(
        data,
        indicators_selector,
        ComposeStrategiesListMethod.READ,
        old_strategies_file_name="dev_strategies_5_indicators.json",
        new_strategies_file_name="strategies.json",
        indicators_filter=[],
        plot=False,
    )


def run_plotting_for_active_strategies(indicators_selector: List[Tuple[str, str]]):
    resolution = "5m"
    period_days = 10

    data = Storage(OMX30_YAHOO, resolution=resolution).read()
    data = data.loc[
        data.index >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=period_days)
    ]

    backtest(
        data.copy(),
        indicators_selector,
        ComposeStrategiesListMethod.READ,
        old_strategies_file_name="strategies.json",
        new_strategies_file_name=None,
        indicators_filter=[],
        plot=True,
    )


def run_test_for_selected_indicators(indicators_selector: List[Tuple[str, str]]):
    resolution = "5m"
    period_days = 60

    data = Storage(OMX30_YAHOO, resolution=resolution).read()
    data = data.loc[
        data.index >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=period_days)
    ]

    indicator_to_test = "KVO"

    for fast, slow, signal in (
        # [(34, 55, 13)]
        [(ifast, 55, 18) for ifast in [15, 20, 25, 30, 40, 45]]
        + [(34, islow, 18) for islow in [40, 45, 50, 60, 65]]
    ):
        kwargs = {"fast": fast, "slow": slow, "signal": signal}

        log.warning(f"Testing for {indicator_to_test}_{kwargs.items()}")
        backtest(
            data.copy(),
            indicators_selector,
            ComposeStrategiesListMethod.EXTEND,
            old_strategies_file_name="dev_strategies_4_indicators.json",
            new_strategies_file_name=f"dev_strategies_5_indicators_{indicator_to_test}_"
            + f"{'_'.join([f'{k}={v}' for k, v in kwargs.items()])}.json",
            indicators_filter=[indicator_to_test],
            plot=False,
            **kwargs,
        )


if __name__ == "__main__":
    indicators_selector: List[Tuple[str, str]] = [
        ("Trend", "ADX"),  # buy / sell
        ("Trend", "TII"),  # buy / sell
        ("Trend", "PSAR"),  # buy / sell
        ("Trend", "CHOP"),  # exit
        ("Overlap", "LINREG"),  # buy / sell
        ("Overlap", "GHLA"),  # buy / sell
        ("Overlap", "SUPERTREND"),  # buy / sell
        ("Momentum", "MACD_DEMA"),  # buy / sell
        ("Momentum", "STC"),  # buy / sell
        ("Momentum", "CCI"),  # buy / sell
        ("Momentum", "RVGI"),  # buy / sell
        ("Momentum", "STOCH"),  # buy / sell
        ("Cycles", "EBSW"),  # buy / sell
        ("Volatility", "STARC"),  # buy / sell
        ("Volatility", "MASSI"),  # buy / sell
        ("Volatility", "BBANDS"),  # buy / sell
        ("Volatility", "ACCBANDS"),  # buy / sell
        # ("Volume", "PVT"),  # buy / sell
        # ("Volume", "ADOSC"),  # buy / sell
        # ("Volume", "CMF"),  # buy / sell (exit?)
        ("Volume", "KVO"),  # buy / sell
    ]

    # run_full_strategies_generation(indicators_selector)
    # run_test_for_selected_indicators(indicators_selector)
    run_plotting_for_active_strategies(indicators_selector)
