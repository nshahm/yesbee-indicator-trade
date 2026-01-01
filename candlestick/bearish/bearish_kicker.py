from typing import List
from ..types import Candle

def is_bearish_kicker(candles: List[Candle]) -> bool:
    """
    Bearish Kicker
    A bearish reversal pattern consisting of a bullish candle followed by a bearish candle that gaps down.
    """
    if len(candles) < 2:
        return False
    prev = candles[-2]
    curr = candles[-1]
    
    prev_is_bullish = prev.close > prev.open
    curr_is_bearish = curr.close < curr.open
    gaps_down = curr.open < prev.open
    
    return prev_is_bullish and curr_is_bearish and gaps_down
