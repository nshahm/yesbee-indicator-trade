from typing import List
from ..types import Candle

def is_three_white_soldiers(candles: List[Candle]) -> bool:
    """
    Three White Soldiers
    A bullish reversal pattern consisting of three consecutive long bullish candles.
    """
    if len(candles) < 3:
        return False
    first = candles[-3]
    second = candles[-2]
    third = candles[-1]
    
    all_bullish = first.close > first.open and second.close > second.open and third.close > third.open
    consecutive_closes = second.close > first.close and third.close > second.close
    opens_inside = (first.open < second.open < first.close) and \
                   (second.open < third.open < second.close)
    
    return all_bullish and consecutive_closes and opens_inside
