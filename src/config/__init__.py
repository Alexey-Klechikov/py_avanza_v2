import platform

from config.settings import SettingsWatchlist, TradeSettings

DATA_COLUMNS = ["Open", "High", "Low", "Close", "Volume"]

DRY_RUN: bool = platform.system() == "Darwin"

SETTINGS = TradeSettings()
SETTINGS_WATCHLIST = SettingsWatchlist()
