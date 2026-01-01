from typing import List
from ..types import Candle

def is_shooting_star(candles: List[Candle]) -> bool:
    """
    Shooting Star
    A bearish reversal pattern that forms at the top of an uptrend.
    It has a small body and a long upper wick.
    """
    if not candles:
        return False
    candle = candles[-1]
    body_size = abs(candle.close - candle.open)
    upper_wick = candle.high - max(candle.open, candle.close)
    lower_wick = min(candle.open, candle.close) - candle.low
    
    return upper_wick > body_size * 2 and lower_wick < body_size
