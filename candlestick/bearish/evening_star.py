from typing import List
from ..types import Candle

def is_evening_star(candles: List[Candle]) -> bool:
    """
    Evening Star
    A bearish reversal pattern consisting of a large bullish candle,
    followed by a small-bodied candle that gaps up, and then a large bearish candle.
    """
    if len(candles) < 3:
        return False
    first = candles[-3]
    second = candles[-2]
    third = candles[-1]
    
    first_is_bullish = first.close > first.open
    first_range = first.high - first.low
    if first_range == 0: return False
    second_is_small = abs(second.close - second.open) < first_range * 0.3
    third_is_bearish = third.close < third.open
    
    second_gaps_up = second.low > max(first.open, first.close)
    third_closes_below_midpoint = third.close < (first.open + first.close) / 2
    
    return first_is_bullish and second_is_small and third_is_bearish and second_gaps_up and third_closes_below_midpoint
