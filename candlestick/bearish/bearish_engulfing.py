from typing import List
from ..types import Candle

def is_bearish_engulfing(candles: List[Candle]) -> bool:
    """
    Bearish Engulfing
    A bearish reversal pattern where a small bullish candle is followed by a larger bearish candle
    that completely overlaps or engulfs the previous candle's body.
    """
    if len(candles) < 2:
        return False
    prev = candles[-2]
    curr = candles[-1]
    
    prev_is_bullish = prev.close > prev.open
    curr_is_bearish = curr.close < curr.open
    engulfs = curr.close < prev.open and curr.open > prev.close
    
    return prev_is_bullish and curr_is_bearish and engulfs
