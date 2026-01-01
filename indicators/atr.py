import pandas as pd
import pandas_ta as ta
from typing import List
from candlestick import Candle

ATR_PERIOD = 14

def calculate_atr(candles: List[Candle], period: int = ATR_PERIOD) -> pd.Series:
    """
    Calculates ATR for a list of candles using pandas-ta.
    """
    if not candles:
        return pd.Series()
        
    df = pd.DataFrame([c.__dict__ for c in candles])
    atr = ta.atr(df['high'], df['low'], df['close'], length=period)
    
    return atr

def get_current_atr(candles: List[Candle], period: int = ATR_PERIOD) -> float:
    """
    Returns the most recent ATR value.
    """
    atr_series = calculate_atr(candles, period)
    if atr_series.empty:
        return 0.0
        
    return float(atr_series.iloc[-1])
