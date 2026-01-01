from typing import List
from ..types import Candle

def is_rising_three(candles: List[Candle]) -> bool:
    """
    Rising Three Methods
    A bullish continuation pattern consisting of a long bullish candle,
    followed by three small bearish candles contained within the first candle's range,
    and then another long bullish candle.
    """
    if len(candles) < 5:
        return False
    first = candles[-5]
    middle = candles[-4:-1]
    last = candles[-1]
    
    first_is_bullish = first.close > first.open
    last_is_bullish = last.close > last.open
    last_closes_above_first = last.close > first.close
    
    middle_are_contained = all(c.high < first.high and c.low > first.low for c in middle)
    middle_are_bearish = all(c.close < c.open for c in middle)
    
    return first_is_bullish and last_is_bullish and last_closes_above_first and middle_are_contained and middle_are_bearish
