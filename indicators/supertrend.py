import pandas as pd
import pandas_ta as ta
from typing import List
from candlestick import Candle

def calculate_supertrend(candles: List[Candle], period: int = 10, multiplier: float = 3.0) -> pd.DataFrame:
    """
    Calculates SuperTrend for a list of candles using pandas-ta.
    """
    if not candles:
        return pd.DataFrame()
        
    df = pd.DataFrame([c.__dict__ for c in candles])
    st = ta.supertrend(df['high'], df['low'], df['close'], length=period, multiplier=multiplier)
    
    return st

def get_current_supertrend(candles: List[Candle], period: int = 10, multiplier: float = 3.0) -> dict:
    """
    Returns the most recent SuperTrend values.
    """
    st_df = calculate_supertrend(candles, period, multiplier)
    if st_df is None or st_df.empty:
        return {"SUPERT_10_3.0": 0.0, "SUPERTd_10_3.0": 0, "SUPERTl_10_3.0": 0.0, "SUPERTs_10_3.0": 0.0}
        
    return st_df.iloc[-1].to_dict()
