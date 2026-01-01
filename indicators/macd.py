import pandas as pd
import pandas_ta as ta
from typing import List, Dict, Union
from candlestick import Candle

def calculate_macd(
    candles: List[Candle], 
    fast: int = 12, 
    slow: int = 26, 
    signal: int = 9
) -> pd.DataFrame:
    """
    Calculates MACD for a list of candles using pandas-ta.
    
    Returns:
        pd.DataFrame: MACD, Histogram, and Signal values
    """
    if not candles:
        return pd.DataFrame()
        
    df = pd.DataFrame([c.__dict__ for c in candles])
    macd_df = ta.macd(df['close'], fast=fast, slow=slow, signal=signal)
    
    return macd_df

def get_current_macd(
    candles: List[Candle], 
    fast: int = 12, 
    slow: int = 26, 
    signal: int = 9
) -> Dict[str, float]:
    """
    Returns the most recent MACD values.
    """
    macd_df = calculate_macd(candles, fast, slow, signal)
    if macd_df is None or macd_df.empty:
        return {"macd": 0.0, "histogram": 0.0, "signal": 0.0}
        
    last_row = macd_df.iloc[-1]
    
    # pandas-ta MACD column names are dynamic based on parameters
    macd_col = f"MACD_{fast}_{slow}_{signal}"
    hist_col = f"MACDh_{fast}_{slow}_{signal}"
    sig_col = f"MACDs_{fast}_{slow}_{signal}"
    
    return {
        "macd": float(last_row[macd_col]),
        "histogram": float(last_row[hist_col]),
        "signal": float(last_row[sig_col])
    }
