from typing import List
from ..types import Candle

def is_inverted_hammer(candles: List[Candle]) -> bool:
    """
    Inverted Hammer
    A bullish reversal pattern that forms during a downtrend.
    It has a small body and a long upper wick.
    """
    if not candles:
        return False
    candle = candles[-1]
    body_size = abs(candle.close - candle.open)
    upper_wick = candle.high - max(candle.open, candle.close)
    lower_wick = min(candle.open, candle.close) - candle.low
    
    return upper_wick > body_size * 2 and lower_wick < body_size
