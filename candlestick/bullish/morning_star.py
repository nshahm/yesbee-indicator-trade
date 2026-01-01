from typing import List
from ..types import Candle

def is_morning_star(candles: List[Candle]) -> bool:
    """
    Morning Star
    A bullish reversal pattern consisting of a large bearish candle, 
    followed by a small-bodied candle that gaps down, and then a large bullish candle.
    """
    if len(candles) < 3:
        return False
    first = candles[-3]
    second = candles[-2]
    third = candles[-1]
    
    first_is_bearish = first.close < first.open
    first_range = first.high - first.low
    if first_range == 0: return False
    second_is_small = abs(second.close - second.open) < first_range * 0.3
    third_is_bullish = third.close > third.open
    
    second_gaps_down = second.high < min(first.open, first.close)
    third_closes_above_midpoint = third.close > (first.open + first.close) / 2
    
    return first_is_bearish and second_is_small and third_is_bullish and second_gaps_down and third_closes_above_midpoint
