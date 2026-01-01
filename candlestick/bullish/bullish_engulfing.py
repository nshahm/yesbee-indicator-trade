from typing import List
from ..types import Candle

def is_bullish_engulfing(candles: List[Candle]) -> bool:
    """
    Bullish Engulfing
    A bullish reversal pattern where a small bearish candle is followed by a larger bullish candle
    that completely overlaps or engulfs the previous candle's body.
    """
    if len(candles) < 2:
        return False
    prev = candles[-2]
    curr = candles[-1]
    
    prev_is_bearish = prev.close < prev.open
    curr_is_bullish = curr.close > curr.open
    engulfs = curr.close > prev.open and curr.open < prev.close
    
    return prev_is_bearish and curr_is_bullish and engulfs
