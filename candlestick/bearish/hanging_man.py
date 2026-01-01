from typing import List
from ..types import Candle

def is_hanging_man(candles: List[Candle]) -> bool:
    """
    Hanging Man
    A bearish reversal pattern that forms at the top of an uptrend.
    It has a small body and a long lower wick.
    """
    if not candles:
        return False
    candle = candles[-1]
    body_size = abs(candle.close - candle.open)
    lower_wick = min(candle.open, candle.close) - candle.low
    upper_wick = candle.high - max(candle.open, candle.close)
    
    return lower_wick > body_size * 2 and upper_wick < body_size
