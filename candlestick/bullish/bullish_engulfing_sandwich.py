from typing import List
from ..types import Candle

def is_bullish_engulfing_sandwich(candles: List[Candle]) -> bool:
    """
    Bullish Engulfing Sandwich
    A bullish pattern where a bullish candle is sandwiched between two bearish candles.
    """
    if len(candles) < 3:
        return False
    first = candles[-3]
    second = candles[-2]
    third = candles[-1]
    
    first_is_bearish = first.close < first.open
    second_is_bullish = second.close > second.open
    third_is_bearish = third.close < third.open
    
    second_engulfs_first = second.close > first.open and second.open < first.close
    total_range_first = first.high - first.low
    if total_range_first == 0: return False
    third_matching_close = abs(third.close - first.close) < total_range_first * 0.1
    
    return first_is_bearish and second_is_bullish and third_is_bearish and second_engulfs_first and third_matching_close
