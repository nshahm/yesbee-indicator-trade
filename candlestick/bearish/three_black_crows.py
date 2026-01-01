from typing import List
from ..types import Candle

def is_three_black_crows(candles: List[Candle]) -> bool:
    """
    Three Black Crows
    A bearish reversal pattern consisting of three consecutive long bearish candles.
    """
    if len(candles) < 3:
        return False
    first = candles[-3]
    second = candles[-2]
    third = candles[-1]
    
    all_bearish = first.close < first.open and second.close < second.open and third.close < third.open
    consecutive_closes = second.close < first.close and third.close < second.close
    opens_inside = (first.open > second.open > first.close) and \
                   (second.open > third.open > second.close)
    
    return all_bearish and consecutive_closes and opens_inside
