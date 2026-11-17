import platform

from config.settings import SettingsWatchlist, TradeStrategies

DATA_COLUMNS = ["Open", "High", "Low", "Close", "Volume"]

DRY_RUN: bool = platform.system() == "Darwin"

SETTINGS = TradeStrategies()
SETTINGS_WATCHLIST = SettingsWatchlist()
