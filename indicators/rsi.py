import pandas as pd
import pandas_ta as ta
from typing import List, Union
from candlestick import Candle

RSI_PERIOD = 14
DEFAULT_NEUTRAL_RSI = 50.0

def calculate_rsi(candles: List[Candle], period: int = RSI_PERIOD) -> pd.Series:
    """
    Calculates RSI for a list of candles using pandas-ta.
    
    Args:
        candles: List of Candle objects
        period: RSI period (default: 14)
        
    Returns:
        pd.Series: RSI values
    """
    if not candles:
        return pd.Series()
        
    # Convert candles to DataFrame
    df = pd.DataFrame([c.__dict__ for c in candles])
    
    # Calculate RSI using pandas-ta
    rsi = ta.rsi(df['close'], length=period)
    
    return rsi

def get_current_rsi(candles: List[Candle], period: int = RSI_PERIOD) -> float:
    """
    Returns the most recent RSI value.
    """
    rsi_series = calculate_rsi(candles, period)
    if rsi_series.empty:
        return DEFAULT_NEUTRAL_RSI  # Default neutral value
        
    return float(rsi_series.iloc[-1])

def check_rsi_signal(rsi_value: float, config: dict) -> str:
    """
    Checks if the RSI value meets entry or exit criteria based on config.
    
    Args:
        rsi_value: Current RSI value
        config: RSI configuration from options.yaml (indicators.rsi)
        
    Returns:
        str: 'CALL', 'PUT', or None
    """
    # Entry logic for CALL
    call_config = config.get('call', {})
    if call_config.get('lower_threshold') <= rsi_value <= call_config.get('upper_threshold'):
        return 'CALL'
        
    # Entry logic for PUT
    put_config = config.get('put', {})
    if put_config.get('lower_threshold') <= rsi_value <= put_config.get('upper_threshold'):
        return 'PUT'
        
    return None
