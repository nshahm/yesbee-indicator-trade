from typing import List
from ..types import Candle

def is_bullish_abandoned_baby(candles: List[Candle]) -> bool:
    """
    Bullish Abandoned Baby
    A rare bullish reversal pattern consisting of a large bearish candle,
    followed by a Doji that gaps completely below the first and third candles.
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
    
    gap_down = second.high < first.low
    gap_up = second.high < third.low
    
    return first_is_bearish and second_is_doji and third_is_bullish and gap_down and gap_up
