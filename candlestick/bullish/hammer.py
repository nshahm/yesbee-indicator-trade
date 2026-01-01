from typing import List
from ..types import Candle

def is_hammer(candles: List[Candle]) -> bool:
    """
    Hammer
    A bullish reversal pattern that forms during a downtrend.
    It has a small body and a long lower wick.
    """
    if not candles:
        return False
    candle = candles[-1]
    body_size = abs(candle.close - candle.open)
    lower_wick = min(candle.open, candle.close) - candle.low
    upper_wick = candle.high - max(candle.open, candle.close)
    
    return lower_wick > body_size * 2 and upper_wick < body_size
