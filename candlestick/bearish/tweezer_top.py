from typing import List
from ..types import Candle

def is_tweezer_top(candles: List[Candle]) -> bool:
    """
    Tweezer Top
    A bearish reversal pattern where two candles have matching or very close highs.
    """
    if len(candles) < 2:
        return False
    prev = candles[-2]
    curr = candles[-1]
    
    total_range_prev = prev.high - prev.low
    if total_range_prev == 0: return False
    
    matching_highs = abs(prev.high - curr.high) < total_range_prev * 0.05
    prev_is_bullish = prev.close > prev.open
    curr_is_bearish = curr.close < curr.open
    
    return prev_is_bullish and curr_is_bearish and matching_highs
