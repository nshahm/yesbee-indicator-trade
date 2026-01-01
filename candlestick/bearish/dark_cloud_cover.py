from typing import List
from ..types import Candle

def is_dark_cloud_cover(candles: List[Candle]) -> bool:
    """
    Dark Cloud Cover
    A bearish reversal pattern where a bullish candle is followed by a bearish candle
    that opens higher but closes below the midpoint of the previous candle's body.
    """
    if len(candles) < 2:
        return False
    prev = candles[-2]
    curr = candles[-1]
    
    prev_is_bullish = prev.close > prev.open
    curr_is_bearish = curr.close < curr.open
    opens_higher = curr.open > prev.high
    closes_below_midpoint = curr.close < (prev.open + prev.close) / 2
    closes_above_open = curr.close > prev.open
    
    return prev_is_bullish and curr_is_bearish and opens_higher and closes_below_midpoint and closes_above_open
