from config.settings_hold import HoldOMX_DT, HoldOMX_Main
from config.settings_trade import TradeNASDAQ, TradeOMX

ACCOUNT_USERNAME: str = "ava_elbe"
DATA_COLUMNS = ["Open", "High", "Low", "Close", "Volume"]

SETTINGS_TRADE_OMX = TradeOMX()
SETTINGS_TRADE_NASDAQ = TradeNASDAQ()

SETTINGS_HOLD_OMX_DT = HoldOMX_DT()
SETTINGS_HOLD_OMX_MAIN = HoldOMX_Main()
