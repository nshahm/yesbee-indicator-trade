from typing import List
from ..types import Candle

def is_doji(candles: List[Candle]) -> bool:
    """
    Doji
    A neutral pattern where the open and close are nearly equal.
    """
    if not candles:
        return False
    candle = candles[-1]
    body_size = abs(candle.close - candle.open)
    total_range = candle.high - candle.low
    
    if total_range == 0: return False
    return body_size < total_range * 0.1
