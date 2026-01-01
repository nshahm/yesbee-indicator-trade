from typing import List
from ..types import Candle

def is_morning_doji_star(candles: List[Candle]) -> bool:
    """
    Morning Doji Star
    A bullish reversal pattern consisting of a large bearish candle, followed by a Doji that gaps down,
    and then a large bullish candle that closes above the midpoint of the first candle.
    """
    if len(candles) < 3:
        return False
    first = candles[-3]
    second = candles[-2]
    third = candles[-1]
    
    first_is_bearish = first.close < first.open
    second_range = second.high - second.low
    second_is_doji = second_range > 0 and abs(second.close - second.open) < second_range * 0.1
    third_is_bullish = third.close > third.open
    
    second_gaps_down = second.high < min(first.open, first.close)
    third_closes_above_midpoint = third.close > (first.open + first.close) / 2
    
    return first_is_bearish and second_is_doji and third_is_bullish and second_gaps_down and third_closes_above_midpoint
