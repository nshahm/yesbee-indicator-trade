from typing import List
from ..types import Candle

def is_bullish_spinning_top(candles: List[Candle]) -> bool:
    """
    Bullish Spinning Top
    A bullish pattern with a small body and long upper and lower wicks.
    """
    if not candles:
        return False
    candle = candles[-1]
    body_size = abs(candle.close - candle.open)
    upper_wick = candle.high - max(candle.open, candle.close)
    lower_wick = min(candle.open, candle.close) - candle.low
    is_bullish = candle.close > candle.open
    total_range = candle.high - candle.low
    
    if total_range == 0: return False
    return is_bullish and body_size < total_range * 0.3 and upper_wick > body_size and lower_wick > body_size
