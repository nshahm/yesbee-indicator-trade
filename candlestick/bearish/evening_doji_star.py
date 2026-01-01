from typing import List
from ..types import Candle

def is_evening_doji_star(candles: List[Candle]) -> bool:
    """
    Evening Doji Star
    A bearish reversal pattern consisting of a large bullish candle, followed by a Doji that gaps up,
    and then a large bearish candle that closes below the midpoint of the first candle.
    """
    if len(candles) < 3:
        return False
    first = candles[-3]
    second = candles[-2]
    third = candles[-1]
    
    first_is_bullish = first.close > first.open
    second_range = second.high - second.low
    second_is_doji = second_range > 0 and abs(second.close - second.open) < second_range * 0.1
    third_is_bearish = third.close < third.open
    
    second_gaps_up = second.low > max(first.open, first.close)
    third_closes_below_midpoint = third.close < (first.open + first.close) / 2
    
    return first_is_bullish and second_is_doji and third_is_bearish and second_gaps_up and third_closes_below_midpoint
