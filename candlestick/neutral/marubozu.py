from typing import List
from ..types import Candle

def is_marubozu(candles: List[Candle]) -> bool:
    """
    Marubozu
    A pattern with a long body and little to no wicks.
    """
    if not candles:
        return False
    candle = candles[-1]
    body_size = abs(candle.close - candle.open)
    total_range = candle.high - candle.low
    
    if total_range == 0: return False
    return body_size > total_range * 0.9
