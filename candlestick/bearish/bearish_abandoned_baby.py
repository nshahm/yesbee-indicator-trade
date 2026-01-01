from typing import List
from ..types import Candle

def is_bearish_abandoned_baby(candles: List[Candle]) -> bool:
    """
    Bearish Abandoned Baby
    A rare bearish reversal pattern consisting of a large bullish candle,
    followed by a Doji that gaps completely above the first and third candles.
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
    
    gap_up = second.low > first.high
    gap_down = second.low > third.high
    
    return first_is_bullish and second_is_doji and third_is_bearish and gap_up and gap_down
