"""Multi-timeframe data fetcher for Zerodha Kite API."""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
from kiteconnect import KiteConnect

logger = logging.getLogger(__name__)


class TimeframeConverter:
    """Convert between various timeframe formats."""
    
    TIMEFRAME_TO_MINUTES = {
        '1m': 1,
        '1min': 1,
        '5m': 5,
        '5min': 5,
        '15m': 15,
        '15min': 15,
        '30m': 30,
        '30min': 30,
        '1h': 60,
        '60m': 60,
        '60min': 60,
        '1hour': 60,
        '2h': 120,
        '2hour': 120,
        '4h': 240,
        '4hour': 240,
        'daily': 1440,
        'd': 1440,
        'weekly': 10080,
        'w': 10080,
        'monthly': 43200,
        'mo': 43200,
    }
    
    KITE_INTERVAL_MAP = {
        '1m': 'minute',
        '1min': 'minute',
        '5m': '5minute',
        '5min': '5minute',
        '15m': '15minute',
        '15min': '15minute',
        '30m': '30minute',
        '30min': '30minute',
        '1h': '60minute',
        '60m': '60minute',
        '60min': '60minute',
        '1hour': '60minute',
        '2h': '2hour',
        '2hour': '2hour',
        '4h': '4hour',
        '4hour': '4hour',
        'daily': 'day',
        'd': 'day',
        'weekly': 'week',
        'w': 'week',
        'monthly': 'month',
        'mo': 'month',
    }
    
    @classmethod
    def to_minutes(cls, timeframe: str) -> int:
        """Convert timeframe string to minutes."""
        tf = timeframe.lower()
        if tf in cls.TIMEFRAME_TO_MINUTES:
            return cls.TIMEFRAME_TO_MINUTES[tf]
        raise ValueError(f"Unknown timeframe: {timeframe}")
    
    @classmethod
    def to_kite_interval(cls, timeframe: str) -> str:
        """Convert timeframe to Kite Connect format."""
        tf = timeframe.lower()
        if tf in cls.KITE_INTERVAL_MAP:
            return cls.KITE_INTERVAL_MAP[tf]
        raise ValueError(f"Unknown timeframe: {timeframe}")


class CandalstickDataFrame:
    """Wrapper for candlestick data with OHLCV columns."""
    
    def __init__(self, data: List[Dict]):
        """Initialize from Kite historical data response."""
        self.df = self._create_dataframe(data)
    
    def _create_dataframe(self, data: List[Dict]) -> pd.DataFrame:
        """Create DataFrame from Kite historical data."""
        if not data:
            return pd.DataFrame(columns=['date', 'open', 'high', 'low', 'close', 'volume'])
        
        processed_data = []
        for candle in data:
            processed_data.append({
                'date': candle[0],
                'open': candle[1],
                'high': candle[2],
                'low': candle[3],
                'close': candle[4],
                'volume': candle[5] if len(candle) > 5 else 0,
                'oi': candle[6] if len(candle) > 6 else 0,
            })
        
        df = pd.DataFrame(processed_data)
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        df = df.astype({
            'open': 'float64',
            'high': 'float64',
            'low': 'float64',
            'close': 'float64',
            'volume': 'int64',
        })
        return df
    
    def get_dataframe(self) -> pd.DataFrame:
        """Return the underlying DataFrame."""
        return self.df
    
    def __len__(self) -> int:
        """Get number of candles."""
        return len(self.df)
    
    def __getitem__(self, key):
        """Support DataFrame-like indexing."""
        return self.df[key]
    
    @property
    def iloc(self):
        """Support iloc for positional indexing."""
        return self.df.iloc
    
    @property
    def loc(self):
        """Support loc for label-based indexing."""
        return self.df.loc


class MultiTimeframeDataFetcher:
    """Fetch market data for multiple timeframes from Zerodha Kite."""
    
    def __init__(self, kite_client: KiteConnect, config: Optional[Dict] = None):
        """Initialize multi-timeframe data fetcher.
        
        Args:
            kite_client: Initialized KiteConnect instance
            config: Optional configuration dictionary with timeframes and lookback
        """
        self.kite = kite_client
        self.config = config or {}
        self.logger = logger
        self._cache = {}
        self._last_fetch_time = {}
        
        self.timeframes = self.config.get('timeframes', ['5min', '15min'])
        self.lookback_days = self.config.get('lookback_days', 5)
        self.cache_ttl_seconds = self.config.get('cache_ttl_seconds', 60)
    
    def fetch_data(self, instrument_token: str, timeframes: Optional[List[str]] = None,
                   days_back: Optional[int] = None) -> Dict[str, pd.DataFrame]:
        """Fetch data for multiple timeframes.
        
        Args:
            instrument_token: Kite instrument token (e.g., "NSE:NIFTY50")
            timeframes: List of timeframes to fetch (e.g., ['5min', '15min'])
            days_back: Number of days to fetch data for
        
        Returns:
            Dictionary mapping timeframe -> DataFrame
        
        Example:
            fetcher = MultiTimeframeDataFetcher(kite_client)
            data = fetcher.fetch_data('NSE:NIFTY50', timeframes=['5min', '15min'])
            df_5min = data['5min'].get_dataframe()
            df_15min = data['15min'].get_dataframe()
        """
        if timeframes is None:
            timeframes = self.timeframes
        
        if days_back is None:
            days_back = self.lookback_days
        
        result = {}
        
        for timeframe in timeframes:
            try:
                self.logger.info(f"Fetching {timeframe} data for {instrument_token}")
                df = self._fetch_single_timeframe(
                    instrument_token, timeframe, days_back
                )
                result[timeframe] = df
                self.logger.info(f"Fetched {len(df)} candles for {timeframe}")
            except Exception as e:
                self.logger.error(f"Error fetching {timeframe} data: {e}")
                result[timeframe] = None
        
        return result
    
    def _fetch_single_timeframe(self, instrument_token: str, timeframe: str,
                               days_back: int) -> CandalstickDataFrame:
        """Fetch data for a single timeframe.
        
        Args:
            instrument_token: Kite instrument token
            timeframe: Timeframe string (e.g., '5min')
            days_back: Number of days to fetch
        
        Returns:
            CandalstickDataFrame object
        """
        cache_key = f"{instrument_token}:{timeframe}"
        
        if cache_key in self._cache:
            cached_time = self._last_fetch_time.get(cache_key, 0)
            if (datetime.now() - cached_time).total_seconds() < self.cache_ttl_seconds:
                self.logger.debug(f"Using cached data for {cache_key}")
                return self._cache[cache_key]
        
        try:
            kite_interval = TimeframeConverter.to_kite_interval(timeframe)
            
            to_date = datetime.now()
            from_date = to_date - timedelta(days=days_back)
            
            self.logger.debug(
                f"Fetching {instrument_token} {kite_interval} "
                f"from {from_date} to {to_date}"
            )
            
            data = self.kite.historical_data(
                instrument_token=instrument_token,
                from_date=from_date,
                to_date=to_date,
                interval=kite_interval
            )
            
            if not data:
                self.logger.warning(f"No data received for {instrument_token} {timeframe}")
                return CandalstickDataFrame([])
            
            df = CandalstickDataFrame(data)
            
            self._cache[cache_key] = df
            self._last_fetch_time[cache_key] = datetime.now()
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error fetching {timeframe} data: {e}")
            raise
    
    def fetch_live_data(self, instrument_token: str) -> Optional[Dict]:
        """Fetch latest quote data (LTP, bid, ask, etc.)
        
        Args:
            instrument_token: Kite instrument token
        
        Returns:
            Quote data dictionary or None
        """
        try:
            quote = self.kite.quote(instrument_token)
            if instrument_token in quote.get('data', {}):
                return quote['data'][instrument_token]
            return None
        except Exception as e:
            self.logger.error(f"Error fetching live data for {instrument_token}: {e}")
            return None
    
    def resample_data(self, df: pd.DataFrame, from_timeframe: str,
                     to_timeframe: str) -> pd.DataFrame:
        """Resample data from one timeframe to another.
        
        Args:
            df: Input DataFrame
            from_timeframe: Source timeframe (e.g., '5min')
            to_timeframe: Target timeframe (e.g., '15min')
        
        Returns:
            Resampled DataFrame
        """
        try:
            from_minutes = TimeframeConverter.to_minutes(from_timeframe)
            to_minutes = TimeframeConverter.to_minutes(to_timeframe)
            
            if from_minutes > to_minutes:
                self.logger.warning(
                    f"Cannot resample from {from_timeframe} to {to_timeframe}: "
                    f"source timeframe is larger"
                )
                return df
            
            rule = f"{to_minutes}T"
            
            resampled = df.resample(rule).agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum',
            })
            
            resampled = resampled.dropna()
            
            return resampled
            
        except Exception as e:
            self.logger.error(f"Error resampling data: {e}")
            raise
    
    def align_timeframes(self, data_dict: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """Align multiple timeframe DataFrames by timestamp.
        
        Ensures all timeframes have matching timestamps for synchronization.
        
        Args:
            data_dict: Dictionary of timeframe -> DataFrame
        
        Returns:
            Aligned data dictionary
        """
        if not data_dict:
            return {}
        
        try:
            all_dates = set()
            
            for df in data_dict.values():
                if df is not None and len(df) > 0:
                    all_dates.update(df.index)
            
            if not all_dates:
                self.logger.warning("No data to align")
                return data_dict
            
            aligned_dict = {}
            for timeframe, df in data_dict.items():
                if df is None:
                    continue
                
                aligned_df = df.reindex(sorted(all_dates), method='ffill')
                aligned_dict[timeframe] = aligned_df
            
            self.logger.info(f"Aligned {len(aligned_dict)} timeframes")
            return aligned_dict
            
        except Exception as e:
            self.logger.error(f"Error aligning timeframes: {e}")
            return data_dict
    
    def clear_cache(self, older_than_seconds: Optional[int] = None):
        """Clear cached data.
        
        Args:
            older_than_seconds: Only clear data older than this duration
        """
        if older_than_seconds is None:
            self._cache.clear()
            self._last_fetch_time.clear()
            self.logger.info("Cleared all cached data")
        else:
            current_time = datetime.now()
            keys_to_remove = []
            
            for key, fetch_time in self._last_fetch_time.items():
                age = (current_time - fetch_time).total_seconds()
                if age > older_than_seconds:
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del self._cache[key]
                del self._last_fetch_time[key]
            
            self.logger.info(f"Cleared {len(keys_to_remove)} cached entries")
