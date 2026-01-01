from typing import List
from ..types import Candle

def is_bullish_kicker(candles: List[Candle]) -> bool:
    """
    Bullish Kicker
    A bullish reversal pattern consisting of a bearish candle followed by a bullish candle that gaps up.
    """
    if len(candles) < 2:
        return False
    prev = candles[-2]
    curr = candles[-1]
    
    prev_is_bearish = prev.close < prev.open
    curr_is_bullish = curr.close > curr.open
    gaps_up = curr.open > prev.open
    
    return prev_is_bearish and curr_is_bullish and gaps_up
