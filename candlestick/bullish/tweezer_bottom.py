from typing import List
from ..types import Candle

def is_tweezer_bottom(candles: List[Candle]) -> bool:
    """
    Tweezer Bottom
    A bullish reversal pattern where two candles have matching or very close lows.
    """
    if len(candles) < 2:
        return False
    prev = candles[-2]
    curr = candles[-1]
    
    total_range_prev = prev.high - prev.low
    if total_range_prev == 0: return False
    
    matching_lows = abs(prev.low - curr.low) < total_range_prev * 0.05
    prev_is_bearish = prev.close < prev.open
    curr_is_bullish = curr.close > curr.open
    
    return prev_is_bearish and curr_is_bullish and matching_lows
