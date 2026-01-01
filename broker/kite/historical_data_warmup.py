"""Historical data warmup loader for initializing indicators with past candles."""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
from kiteconnect import KiteConnect

from .multi_timeframe_fetcher import MultiTimeframeDataFetcher, TimeframeConverter
from indicators.indicator_engine import IndicatorEngine

logger = logging.getLogger(__name__)


class HistoricalDataWarmup:
    """Load historical candlestick data as warmup for indicator initialization."""
    
    def __init__(self, kite_client: KiteConnect):
        """Initialize warmup loader.
        
        Args:
            kite_client: Initialized KiteConnect instance
        """
        self.kite = kite_client
        self.fetcher = MultiTimeframeDataFetcher(kite_client)
        self.warmup_cache = {}
        self.indicator_cache = {}
    
    def calculate_lookback_days(self, timeframe: str, num_candles: int = 30) -> int:
        """Calculate how many days back to fetch for desired number of candles.
        
        Calculates based on actual trading minutes, accounting for weekends/holidays.
        Works correctly even outside trading hours.
        
        Args:
            timeframe: Timeframe string (e.g., '5min', '15min', 'daily')
            num_candles: Number of candles desired (default: 30)
        
        Returns:
            Number of days to look back (includes buffer for weekends/holidays)
        """
        minutes_per_candle = TimeframeConverter.to_minutes(timeframe)
        total_minutes = minutes_per_candle * num_candles
        
        if timeframe in ['daily', 'weekly', 'monthly']:
            return num_candles * 2
        
        trading_hours_per_day = 6.5
        trading_minutes_per_day = trading_hours_per_day * 60
        
        days_needed = (total_minutes / trading_minutes_per_day) * 2
        return max(10, int(days_needed) + 5)
    
    def calculate_time_range(self, timeframe: str, num_candles: int = 30) -> Tuple[datetime, datetime]:
        """Calculate start and end time for historical data fetch.
        
        Calculates based on number of candles needed and timeframe.
        Works correctly even outside trading hours by extending lookback appropriately.
        
        Args:
            timeframe: Timeframe string (e.g., '5min', '15min', 'daily')
            num_candles: Number of candles needed
        
        Returns:
            Tuple of (from_date, to_date) for API call
        """
        to_date = datetime.now()
        
        lookback_days = self.calculate_lookback_days(timeframe, num_candles)
        from_date = to_date - timedelta(days=lookback_days)
        
        logger.info(
            f"Calculating time range for {timeframe}: "
            f"Need {num_candles} candles, looking back {lookback_days} days "
            f"from {to_date.strftime('%Y-%m-%d %H:%M')} "
            f"to {from_date.strftime('%Y-%m-%d %H:%M')}"
        )
        
        return from_date, to_date
    
    def fetch_warmup_data(self, instrument_token: str, 
                         lower_timeframe: str, higher_timeframe: str,
                         num_candles: int = 30) -> Dict[str, pd.DataFrame]:
        """Fetch historical data for warmup on both timeframes.
        
        Args:
            instrument_token: Kite instrument token (e.g., 'NSE:NIFTY50')
            lower_timeframe: Lower timeframe (e.g., '5min')
            higher_timeframe: Higher timeframe (e.g., '15min')
            num_candles: Number of warmup candles needed (default: 30)
        
        Returns:
            Dictionary mapping timeframe -> DataFrame with OHLCV data
        
        Raises:
            ValueError: If fetch fails for both timeframes
        """
        cache_key = f"{instrument_token}:{lower_timeframe}:{higher_timeframe}"
        
        if cache_key in self.warmup_cache:
            logger.debug(f"Using cached warmup data for {cache_key}")
            return self.warmup_cache[cache_key]
        
        logger.info(
            f"Fetching warmup data for {instrument_token} "
            f"({lower_timeframe}, {higher_timeframe}) - {num_candles} candles"
        )
        
        result = {}
        timeframes = [lower_timeframe, higher_timeframe]
        
        for timeframe in timeframes:
            try:
                from_date, to_date = self.calculate_time_range(timeframe, num_candles)
                
                kite_interval = TimeframeConverter.to_kite_interval(timeframe)
                
                logger.info(
                    f"[WARMUP] Fetching {instrument_token} {kite_interval} "
                    f"from {from_date.strftime('%Y-%m-%d %H:%M:%S')} "
                    f"to {to_date.strftime('%Y-%m-%d %H:%M:%S')} "
                    f"(need {num_candles} candles)"
                )
                
                data = self.kite.historical_data(
                    instrument_token=instrument_token,
                    from_date=from_date,
                    to_date=to_date,
                    interval=kite_interval
                )
                
                if not data:
                    logger.warning(
                        f"[WARMUP] No historical data received for {instrument_token} {timeframe}"
                    )
                    result[timeframe] = None
                    continue
                
                df = self._create_dataframe(data)
                logger.info(
                    f"[WARMUP] Received {len(df)} candles for {timeframe} "
                    f"(requested {num_candles})"
                )
                
                if len(df) < num_candles:
                    logger.warning(
                        f"[WARMUP] Got {len(df)} candles for {timeframe}, "
                        f"requested {num_candles}. Using available data."
                    )
                else:
                    df = df.tail(num_candles).copy()
                    logger.info(f"[WARMUP] Using last {num_candles} candles for {timeframe}")
                
                result[timeframe] = df
                logger.info(
                    f"[WARMUP] Successfully loaded {len(df)} warmup candles for {timeframe} "
                    f"(time range: {df.index[0].strftime('%Y-%m-%d %H:%M')} - "
                    f"{df.index[-1].strftime('%Y-%m-%d %H:%M')})"
                )
                
            except Exception as e:
                logger.error(
                    f"[WARMUP] Error fetching warmup data for {timeframe}: {e}", 
                    exc_info=True
                )
                result[timeframe] = None
        
        if not any(v is not None for v in result.values()):
            logger.error(f"[WARMUP] Failed to fetch warmup data for {instrument_token}")
            raise ValueError(f"Failed to fetch warmup data for {instrument_token}")
        
        self.warmup_cache[cache_key] = result
        logger.info(f"[WARMUP] Cached warmup data for {cache_key}")
        return result
    
    def _create_dataframe(self, data: List[Dict]) -> pd.DataFrame:
        """Create DataFrame from Kite historical data.
        
        Args:
            data: List of candlestick data from Kite API
        
        Returns:
            pandas DataFrame with OHLCV columns
        """
        if not data:
            return pd.DataFrame(columns=['date', 'open', 'high', 'low', 'close', 'volume'])
        
        processed_data = []
        for candle in data:
            processed_data.append({
                'date': candle[0],
                'open': float(candle[1]),
                'high': float(candle[2]),
                'low': float(candle[3]),
                'close': float(candle[4]),
                'volume': int(candle[5]) if len(candle) > 5 else 0,
                'oi': int(candle[6]) if len(candle) > 6 else 0,
            })
        
        df = pd.DataFrame(processed_data)
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        
        return df
    
    def initialize_indicators(self, df: pd.DataFrame, timeframe: str,
                            atr_period: int = 14, rsi_period: int = 14,
                            macd_fast: int = 12, macd_slow: int = 26,
                            macd_signal: int = 9) -> Dict[str, any]:
        """Initialize indicator values from warmup data.
        
        Args:
            df: DataFrame with warmup candles
            timeframe: Timeframe identifier for caching
            atr_period: ATR period (default: 14)
            rsi_period: RSI period (default: 14)
            macd_fast: MACD fast period (default: 12)
            macd_slow: MACD slow period (default: 26)
            macd_signal: MACD signal period (default: 9)
        
        Returns:
            Dictionary with calculated indicator values
        """
        if df is None or df.empty:
            logger.warning(f"Cannot initialize indicators for {timeframe}: empty data")
            return self._get_default_indicators()
        
        try:
            atr_value = IndicatorEngine.get_atr_value(df, atr_period)
            rsi_value = IndicatorEngine.get_rsi_value(df, rsi_period)
            macd_values = IndicatorEngine.get_macd_value(df, macd_fast, macd_slow, macd_signal)
            
            indicators = {
                'timeframe': timeframe,
                'candles_count': len(df),
                'atr': {
                    'value': float(atr_value),
                    'period': atr_period
                },
                'rsi': {
                    'value': float(rsi_value),
                    'period': rsi_period
                },
                'macd': {
                    'value': float(macd_values['macd']),
                    'signal': float(macd_values['signal']),
                    'histogram': float(macd_values['histogram']),
                    'fast_period': macd_fast,
                    'slow_period': macd_slow,
                    'signal_period': macd_signal
                },
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(
                f"Initialized indicators for {timeframe}: "
                f"ATR={atr_value:.4f}, RSI={rsi_value:.2f}, MACD={macd_values['macd']:.4f}"
            )
            
            return indicators
            
        except Exception as e:
            logger.error(f"Error initializing indicators for {timeframe}: {e}")
            return self._get_default_indicators()
    
    def _get_default_indicators(self) -> Dict:
        """Get default indicator values."""
        return {
            'atr': {'value': 0.0, 'period': 14},
            'rsi': {'value': 50.0, 'period': 14},
            'macd': {
                'value': 0.0,
                'signal': 0.0,
                'histogram': 0.0,
                'fast_period': 12,
                'slow_period': 26,
                'signal_period': 9
            },
            'timestamp': datetime.now().isoformat()
        }
    
    def load_warmup(self, instrument_token: str, 
                   lower_timeframe: str, higher_timeframe: str,
                   num_candles: int = 30,
                   atr_period: int = 14, rsi_period: int = 14) -> Dict[str, any]:
        """Load warmup data and initialize all indicators.
        
        This is the main entry point for warming up indicators on startup.
        
        Args:
            instrument_token: Kite instrument token
            lower_timeframe: Lower timeframe for trading (e.g., '5min')
            higher_timeframe: Higher timeframe for confirmation (e.g., '15min')
            num_candles: Number of warmup candles (default: 30)
            atr_period: ATR period (default: 14)
            rsi_period: RSI period (default: 14)
        
        Returns:
            Dictionary with warmup data and initialized indicators:
            {
                'status': 'success' | 'partial' | 'failed',
                'instrument_token': 'NSE:NIFTY50',
                'lower_timeframe': {...warmup_data...},
                'higher_timeframe': {...warmup_data...},
                'indicators': {
                    'lower_timeframe': {...indicator_values...},
                    'higher_timeframe': {...indicator_values...}
                },
                'timestamp': '2024-12-23T...'
            }
        
        Raises:
            ValueError: If no data can be fetched
        """
        logger.info(
            f"Starting warmup load for {instrument_token} "
            f"({lower_timeframe}, {higher_timeframe})"
        )
        
        try:
            warmup_data = self.fetch_warmup_data(
                instrument_token, lower_timeframe, higher_timeframe, num_candles
            )
            
            result = {
                'status': 'success',
                'instrument_token': instrument_token,
                'num_candles_requested': num_candles,
                'lower_timeframe': {},
                'higher_timeframe': {},
                'indicators': {},
                'timestamp': datetime.now().isoformat()
            }
            
            timeframes_success = 0
            
            for timeframe, df in warmup_data.items():
                if df is not None and not df.empty:
                    result[timeframe] = {
                        'candles': len(df),
                        'start_time': df.index[0].isoformat(),
                        'end_time': df.index[-1].isoformat(),
                        'ohlcv': {
                            'open': float(df['open'].iloc[-1]),
                            'high': float(df['high'].max()),
                            'low': float(df['low'].min()),
                            'close': float(df['close'].iloc[-1]),
                            'volume': int(df['volume'].sum())
                        }
                    }
                    
                    indicators = self.initialize_indicators(
                        df, timeframe, atr_period, rsi_period
                    )
                    result['indicators'][timeframe] = indicators
                    timeframes_success += 1
                else:
                    result[timeframe] = {'candles': 0, 'status': 'no_data'}
            
            if timeframes_success == 0:
                result['status'] = 'failed'
                logger.error(f"Warmup load failed: no data for any timeframe")
                raise ValueError("No warmup data available for any timeframe")
            elif timeframes_success < 2:
                result['status'] = 'partial'
                logger.warning(f"Warmup load partial: data for {timeframes_success}/2 timeframes")
            
            logger.info(
                f"Warmup load completed: {timeframes_success}/2 timeframes, "
                f"Status: {result['status']}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Warmup load failed: {e}")
            raise
    
    def load_warmup_for_symbols(self, symbols: List[str],
                               lower_timeframe: str, higher_timeframe: str,
                               num_candles: int = 30,
                               atr_period: int = 14, rsi_period: int = 14,
                               instrument_tokens: Optional[Dict[str, str]] = None) -> Dict[str, Dict]:
        """Load warmup data for multiple symbols.
        
        Args:
            symbols: List of symbol names (e.g., ['NIFTY50', 'BANKNIFTY'])
            lower_timeframe: Lower timeframe
            higher_timeframe: Higher timeframe
            num_candles: Number of warmup candles
            atr_period: ATR period
            rsi_period: RSI period
            instrument_tokens: Dict mapping symbol -> token. If None, will use default mapping
        
        Returns:
            Dictionary mapping symbol -> warmup result
        """
        results = {}
        
        logger.info(
            f"[WARMUP] Starting warmup load for {len(symbols)} symbols: {symbols} "
            f"({lower_timeframe}, {higher_timeframe}) - {num_candles} candles"
        )
        
        if instrument_tokens is None:
            instrument_tokens = self._get_default_tokens(symbols)
        
        for idx, symbol in enumerate(symbols, 1):
            try:
                token = instrument_tokens.get(symbol, f"NSE:{symbol}")
                logger.info(
                    f"[WARMUP] [{idx}/{len(symbols)}] Loading warmup for {symbol} ({token}) "
                    f"{lower_timeframe}/{higher_timeframe}"
                )
                
                result = self.load_warmup(
                    token, lower_timeframe, higher_timeframe, 
                    num_candles, atr_period, rsi_period
                )
                results[symbol] = result
                
                logger.info(
                    f"[WARMUP] [{idx}/{len(symbols)}] {symbol} - Status: {result.get('status')} "
                    f"({result.get('lower_timeframe', {}).get('candles', 0)} + "
                    f"{result.get('higher_timeframe', {}).get('candles', 0)} candles)"
                )
                
            except Exception as e:
                logger.error(
                    f"[WARMUP] [{idx}/{len(symbols)}] Failed to load warmup for {symbol}: {e}", 
                    exc_info=True
                )
                results[symbol] = {
                    'status': 'failed',
                    'error': str(e),
                    'symbol': symbol
                }
        
        success_count = sum(1 for r in results.values() if r.get('status') != 'failed')
        logger.info(
            f"[WARMUP] Warmup load complete for {len(results)} symbols. "
            f"Success: {success_count}/{len(symbols)} - "
            f"Failed: {len(results) - success_count}/{len(symbols)}"
        )
        
        return results
    
    def _get_default_tokens(self, symbols: List[str]) -> Dict[str, str]:
        """Get default instrument tokens from config.
        
        Args:
            symbols: List of symbol names
        
        Returns:
            Dictionary mapping symbol -> token
        """
        from .kite_connect import KiteConnectConfig
        
        try:
            config = KiteConnectConfig()
            tokens = {}
            
            for symbol in symbols:
                token = config.get_instrument_token(symbol)
                if token:
                    tokens[symbol] = f"NSE:{token}"
                else:
                    tokens[symbol] = f"NSE:{symbol}"
            
            return tokens
        except Exception as e:
            logger.warning(f"Failed to load instrument tokens from config: {e}")
            return {s: f"NSE:{s}" for s in symbols}
    
    def clear_cache(self):
        """Clear cached warmup data."""
        self.warmup_cache.clear()
        self.indicator_cache.clear()
        logger.info("Cleared warmup cache")
