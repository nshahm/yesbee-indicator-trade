import pandas as pd
import numpy as np
from typing import List, Optional, Dict, Any
from candlestick import Candle

def detect_swings(candles: List[Candle], n: int = 2) -> Dict[str, List[Optional[float]]]:
    """
    Detects swing highs and swing lows.
    A candle whose high/low is greater/less than N candles on both sides.
    """
    highs = [c.high for c in candles]
    lows = [c.low for c in candles]
    
    swing_highs = [None] * len(candles)
    swing_lows = [None] * len(candles)
    
    for i in range(n, len(candles) - n):
        # Swing High: High[i] > High[i-1..i-N] AND High[i] > High[i+1..i+N]
        is_sh = True
        for j in range(1, n + 1):
            if highs[i] <= highs[i-j] or highs[i] <= highs[i+j]:
                is_sh = False
                break
        if is_sh:
            swing_highs[i] = highs[i]
            
        # Swing Low: Low[i] < Low[i-1..i-N] AND Low[i] < Low[i+1..i+N]
        is_sl = True
        for j in range(1, n + 1):
            if lows[i] >= lows[i-j] or lows[i] >= lows[i+j]:
                is_sl = False
                break
        if is_sl:
            swing_lows[i] = lows[i]
            
    return {
        'swing_highs': swing_highs,
        'swing_lows': swing_lows
    }

class MarketStructure:
    def __init__(self, n: int = 2):
        self.n = n
        self.last_hh = None
        self.last_hl = None
        self.last_ll = None
        self.last_lh = None
        
        self.prev_swing_high = None
        self.prev_swing_low = None
        
        # State tracking for patterns
        self.potential_put = False # HH formed, waiting for LH
        self.potential_call = False # LL formed, waiting for LH
        
        self.hh_price = None
        self.hl_price = None
        self.ll_price = None
        self.lh_price = None

    def update(self, candles: List[Candle]) -> Dict[str, Any]:
        if len(candles) < self.n * 2 + 1:
            return {}
            
        swings = detect_swings(candles, self.n)
        
        # We look at the candle at index -1 - n because that's the latest confirmed swing
        idx = len(candles) - 1 - self.n
        
        sh = swings['swing_highs'][idx]
        sl = swings['swing_lows'][idx]
        
        result = {
            'is_hh': False,
            'is_lh': False,
            'is_ll': False,
            'is_hl': False,
            'hh_price': self.hh_price,
            'lh_price': self.lh_price,
            'll_price': self.ll_price,
            'hl_price': self.hl_price
        }

        if sh is not None:
            if self.prev_swing_high is not None:
                if sh > self.prev_swing_high:
                    self.hh_price = sh
                    result['is_hh'] = True
                elif sh < self.prev_swing_high:
                    self.lh_price = sh
                    result['is_lh'] = True
            self.prev_swing_high = sh

        if sl is not None:
            if self.prev_swing_low is not None:
                if sl < self.prev_swing_low:
                    self.ll_price = sl
                    result['is_ll'] = True
                elif sl > self.prev_swing_low:
                    self.hl_price = sl
                    result['is_hl'] = True
            self.prev_swing_low = sl
            
        result.update({
            'hh_price': self.hh_price,
            'lh_price': self.lh_price,
            'll_price': self.ll_price,
            'hl_price': self.hl_price
        })
        
        return result
