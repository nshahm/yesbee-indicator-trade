import pandas as pd
import pandas_ta as ta
from typing import List
from candlestick import Candle

def calculate_ema(candles: List[Candle], period: int) -> pd.Series:
    """
    Calculates EMA for a list of candles using pandas-ta.
    """
    if not candles:
        return pd.Series()
        
    df = pd.DataFrame([c.__dict__ for c in candles])
    ema = ta.ema(df['close'], length=period)
    
    return ema

def get_current_ema(candles: List[Candle], period: int) -> float:
    """
    Returns the most recent EMA value.
    """
    ema_series = calculate_ema(candles, period)
    if ema_series.empty:
        return 0.0
        
    return float(ema_series.iloc[-1])
