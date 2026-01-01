from typing import List
from ..types import Candle

def is_bullish_harami(candles: List[Candle]) -> bool:
    """
    Bullish Harami
    A bullish reversal pattern where a large bearish candle is followed by a small bullish candle
    that is completely contained within the body of the previous candle.
    """
    if len(candles) < 2:
        return False
    prev = candles[-2]
    curr = candles[-1]
    
    prev_is_bearish = prev.close < prev.open
    curr_is_bullish = curr.close > curr.open
    contained = curr.open > prev.close and curr.close < prev.open
    
    return prev_is_bearish and curr_is_bullish and contained
