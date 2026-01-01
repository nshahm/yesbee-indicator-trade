import pandas as pd
import pandas_ta as ta
from typing import List, Union
from candlestick import Candle

ADX_PERIOD = 14

def calculate_adx(candles: List[Candle], period: int = ADX_PERIOD) -> pd.DataFrame:
    """
    Calculates ADX for a list of candles using pandas-ta.
    
    Interpretation:
    - < 18: Sideways
    - 18-25: Weak Trend
    - > 25: Strong Trend
    
    Args:
        candles: List of Candle objects
        period: ADX period (default: 14)
        
    Returns:
        pd.DataFrame: ADX, DMP, and DMN values
    """
    if not candles:
        return pd.DataFrame()
        
    # Convert candles to DataFrame
    df = pd.DataFrame([c.__dict__ for c in candles])
    
    # Calculate ADX using pandas-ta
    # Returns a DataFrame with ADX_14, DMP_14, DMN_14
    adx_df = ta.adx(df['high'], df['low'], df['close'], length=period)
    
    return adx_df

def get_current_adx(candles: List[Candle], period: int = ADX_PERIOD) -> float:
    """
    Returns the most recent ADX value.
    """
    adx_df = calculate_adx(candles, period)
    if adx_df is None or adx_df.empty:
        return 0.0
        
    # Use the first column which is ADX
    return float(adx_df.iloc[-1, 0])
