from typing import List
from ..types import Candle

def is_bearish_harami(candles: List[Candle]) -> bool:
    """
    Bearish Harami
    A bearish reversal pattern where a large bullish candle is followed by a small bearish candle
    that is completely contained within the body of the previous candle.
    """
    if len(candles) < 2:
        return False
    prev = candles[-2]
    curr = candles[-1]
    
    prev_is_bullish = prev.close > prev.open
    curr_is_bearish = curr.close < curr.open
    contained = curr.open < prev.close and curr.close > prev.open
    
    return prev_is_bullish and curr_is_bearish and contained
