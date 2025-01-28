from config.OMX_settings import TradeStrategies as TradeStrategiesOMX
from config.TESLA_settings import TradeStrategies as TradeStrategiesTESLA

ACCOUNT_USERNAME: str = "ava_elbe"
DATA_COLUMNS = ["Open", "High", "Low", "Close", "Volume"]

SETTINGS_TRADE_STRATEGIES_OMX = TradeStrategiesOMX()
SETTINGS_TRADE_STRATEGIES_TESLA = TradeStrategiesTESLA()
