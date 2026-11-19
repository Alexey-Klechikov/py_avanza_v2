from collections.abc import Callable

from pydantic import BaseModel


class IndicatorSignal(BaseModel):
    """Per-bar rules: each takes one bar's record (OHLCV plus indicator columns) and is truthy when it signals."""

    LONG: Callable | None = None
    SHORT: Callable | None = None


class Indicator(BaseModel):
    columns: list[str]
    signal: IndicatorSignal
