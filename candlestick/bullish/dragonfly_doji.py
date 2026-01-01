from typing import List
from ..types import Candle

def is_dragonfly_doji(candles: List[Candle]) -> bool:
    """
    Dragonfly Doji
    A bullish reversal pattern where open, high, and close are the same or very close.
    It has a long lower wick.
    """
    if not candles:
        return False
    candle = candles[-1]
    body_size = abs(candle.close - candle.open)
    upper_wick = candle.high - max(candle.open, candle.close)
    lower_wick = min(candle.open, candle.close) - candle.low
    total_range = candle.high - candle.low
    
    if total_range == 0: return False
    return body_size < total_range * 0.1 and upper_wick < body_size and lower_wick > body_size * 3
