import pandas as pd
import pandas_ta as ta
from typing import List, Dict
from candlestick import Candle

def calculate_stochastic(
    candles: List[Candle],
    k: int = 14,
    d: int = 3,
    smooth_k: int = 3
) -> pd.DataFrame:
    """
    Calculates Stochastic Oscillator for a list of candles using pandas-ta.
    """
    if not candles:
        return pd.DataFrame()
        
    df = pd.DataFrame([c.__dict__ for c in candles])
    stoch_df = ta.stoch(df['high'], df['low'], df['close'], k=k, d=d, smooth_k=smooth_k)
    
    return stoch_df

def get_current_stochastic(
    candles: List[Candle],
    k: int = 14,
    d: int = 3,
    smooth_k: int = 3
) -> Dict[str, float]:
    """
    Returns the most recent Stochastic values (%K and %D).
    """
    stoch_df = calculate_stochastic(candles, k, d, smooth_k)
    if stoch_df is None or stoch_df.empty:
        return {"k": 50.0, "d": 50.0}
        
    last_row = stoch_df.iloc[-1]
    
    k_col = f"STOCHk_{k}_{d}_{smooth_k}"
    d_col = f"STOCHd_{k}_{d}_{smooth_k}"
    
    return {
        "k": float(last_row[k_col]),
        "d": float(last_row[d_col])
    }
