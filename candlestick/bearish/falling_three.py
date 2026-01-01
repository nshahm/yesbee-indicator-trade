from typing import List
from ..types import Candle

def is_falling_three(candles: List[Candle]) -> bool:
    """
    Falling Three Methods
    A bearish continuation pattern consisting of a long bearish candle,
    followed by three small bullish candles contained within the first candle's range,
    and then another long bearish candle.
    """
    if len(candles) < 5:
        return False
    first = candles[-5]
    middle = candles[-4:-1]
    last = candles[-1]
    
    first_is_bearish = first.close < first.open
    last_is_bearish = last.close < last.open
    last_closes_below_first = last.close < first.close
    
    middle_are_contained = all(c.high < first.high and c.low > first.low for c in middle)
    middle_are_bullish = all(c.close > c.open for c in middle)
    
    return first_is_bearish and last_is_bearish and last_closes_below_first and middle_are_contained and middle_are_bullish
