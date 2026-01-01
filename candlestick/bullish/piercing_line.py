from typing import List
from ..types import Candle

def is_piercing_line(candles: List[Candle]) -> bool:
    """
    Piercing Line
    A bullish reversal pattern where a bearish candle is followed by a bullish candle
    that opens lower but closes above the midpoint of the previous candle's body.
    """
    if len(candles) < 2:
        return False
    prev = candles[-2]
    curr = candles[-1]
    
    prev_is_bearish = prev.close < prev.open
    curr_is_bullish = curr.close > curr.open
    opens_lower = curr.open < prev.low
    closes_above_midpoint = curr.close > (prev.open + prev.close) / 2
    closes_below_open = curr.close < prev.open
    
    return prev_is_bearish and curr_is_bullish and opens_lower and closes_above_midpoint and closes_below_open
