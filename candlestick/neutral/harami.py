from typing import List
from ..types import Candle

def is_harami(candles: List[Candle]) -> bool:
    """
    Harami (Neutral)
    A pattern where a large candle is followed by a small candle 
    that is completely contained within the body of the previous candle.
    """
    if len(candles) < 2:
        return False
    prev = candles[-2]
    curr = candles[-1]
    
    prev_body_max = max(prev.open, prev.close)
    prev_body_min = min(prev.open, prev.close)
    curr_body_max = max(curr.open, curr.close)
    curr_body_min = min(curr.open, curr.close)
    
    contained = curr_body_max < prev_body_max and curr_body_min > prev_body_min
    
    return contained
