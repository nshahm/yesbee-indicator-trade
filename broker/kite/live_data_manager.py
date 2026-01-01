"""Live data manager for streaming and maintaining multi-timeframe candles."""

import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from collections import defaultdict
import pandas as pd
from kiteconnect import KiteConnect
try:
    from kiteconnect import WebSocket
except ImportError:
    try:
        from kiteconnect import KiteTicker as WebSocket
    except ImportError:
        WebSocket = None

logger = logging.getLogger(__name__)


class CandleBuilder:
    """Build candles from tick data."""
    
    def __init__(self, timeframe_minutes: int):
        """Initialize candle builder.
        
        Args:
            timeframe_minutes: Timeframe in minutes (e.g., 5, 15)
        """
        self.timeframe_minutes = timeframe_minutes
        self.current_candle = None
        self.candle_start_time = None
    
    def reset_candle(self):
        """Reset current candle."""
        self.current_candle = None
        self.candle_start_time = None
    
    def update_with_tick(self, timestamp: datetime, price: float,
                        volume: int = 1) -> Optional[Dict]:
        """Update candle with tick data.
        
        Returns completed candle when timeframe boundary is crossed, None otherwise.
        """
        if self.candle_start_time is None:
            self._initialize_candle(timestamp, price, volume)
            return None
        
        minutes_elapsed = (timestamp - self.candle_start_time).total_seconds() / 60
        
        if minutes_elapsed >= self.timeframe_minutes:
            completed_candle = self.current_candle.copy()
            self._initialize_candle(timestamp, price, volume)
            return completed_candle
        
        if minutes_elapsed > 0:
            self.current_candle['high'] = max(self.current_candle['high'], price)
            self.current_candle['low'] = min(self.current_candle['low'], price)
            self.current_candle['close'] = price
            self.current_candle['volume'] += volume
        
        return None
    
    def _initialize_candle(self, timestamp: datetime, price: float, volume: int):
        """Initialize a new candle."""
        self.candle_start_time = timestamp
        self.current_candle = {
            'timestamp': timestamp,
            'open': price,
            'high': price,
            'low': price,
            'close': price,
            'volume': volume,
        }
    
    def get_current_candle(self) -> Optional[Dict]:
        """Get current incomplete candle."""
        if self.current_candle:
            return self.current_candle.copy()
        return None


class TimeframeDataStore:
    """Store and manage candles for a specific timeframe."""
    
    def __init__(self, timeframe_minutes: int, max_candles: int = 1000):
        """Initialize data store.
        
        Args:
            timeframe_minutes: Timeframe in minutes
            max_candles: Maximum candles to keep in memory
        """
        self.timeframe_minutes = timeframe_minutes
        self.max_candles = max_candles
        self.candles = []
        self.builder = CandleBuilder(timeframe_minutes)
        self._lock = threading.Lock()
    
    def add_tick(self, timestamp: datetime, price: float,
                volume: int = 1) -> Optional[Dict]:
        """Add tick and potentially complete a candle.
        
        Returns completed candle if timeframe boundary crossed.
        """
        with self._lock:
            completed = self.builder.update_with_tick(timestamp, price, volume)
            
            if completed:
                self.candles.append(completed)
                
                if len(self.candles) > self.max_candles:
                    self.candles.pop(0)
            
            return completed
    
    def get_dataframe(self) -> pd.DataFrame:
        """Get all candles as DataFrame."""
        with self._lock:
            if not self.candles:
                return pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume'])
            
            df = pd.DataFrame(self.candles)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
            return df
    
    def get_last_n_candles(self, n: int) -> pd.DataFrame:
        """Get last N candles as DataFrame."""
        with self._lock:
            candles = self.candles[-n:] if n <= len(self.candles) else self.candles
            
            if not candles:
                return pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume'])
            
            df = pd.DataFrame(candles)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
            return df
    
    def get_current_candle(self) -> Optional[Dict]:
        """Get current incomplete candle."""
        with self._lock:
            return self.builder.get_current_candle()


class LiveDataManager:
    """Manage live data streams for multiple timeframes."""
    
    def __init__(self, kite_client: KiteConnect, config: Optional[Dict] = None):
        """Initialize live data manager.
        
        Args:
            kite_client: Initialized KiteConnect instance
            config: Configuration dict with timeframes, user_id, etc.
        """
        self.kite = kite_client
        self.config = config or {}
        self.logger = logger
        
        self.timeframes = self.config.get('timeframes', ['5min', '15min'])
        self.timeframe_minutes = {
            '1min': 1,
            '5min': 5,
            '15min': 15,
            '30min': 30,
            '60min': 60,
        }
        
        self.stores: Dict[str, Dict[str, TimeframeDataStore]] = defaultdict(dict)
        self.ws = None
        self.ws_connected = False
        self._running = False
        self._callbacks = defaultdict(list)
        self._lock = threading.Lock()
    
    def subscribe_to_instrument(self, instrument_token: str, 
                               timeframes: Optional[List[str]] = None):
        """Subscribe to instrument for live data.
        
        Args:
            instrument_token: Kite instrument token (e.g., "256265")
            timeframes: List of timeframes to track
        """
        if timeframes is None:
            timeframes = self.timeframes
        
        with self._lock:
            for timeframe in timeframes:
                minutes = self.timeframe_minutes.get(timeframe, 5)
                self.stores[instrument_token][timeframe] = TimeframeDataStore(minutes)
        
        self.logger.info(f"Subscribed to {instrument_token} for {timeframes}")
    
    def register_callback(self, instrument_token: str, 
                         callback: Callable[[str, Dict], None]):
        """Register callback for candle completion.
        
        Callback signature: callback(instrument_token, completed_candle_data)
        """
        self._callbacks[instrument_token].append(callback)
        self.logger.debug(f"Registered callback for {instrument_token}")
    
    def start_websocket(self, api_key: str, access_token: str, user_id: str):
        """Start WebSocket connection for live data.
        
        Args:
            api_key: Kite API key
            access_token: Kite access token
            user_id: Kite user ID
        """
        if WebSocket is None:
            self.logger.error("WebSocket/KiteTicker not available in kiteconnect library")
            return
        
        if self.ws_connected:
            self.logger.warning("WebSocket already connected")
            return
        
        try:
            self.ws = WebSocket(api_key, user_id, access_token)
            self.ws.on_connect = self._on_ws_connect
            self.ws.on_message = self._on_ws_message
            self.ws.on_close = self._on_ws_close
            self.ws.on_error = self._on_ws_error
            
            self._running = True
            
            ws_thread = threading.Thread(target=self.ws.connect, daemon=True)
            ws_thread.start()
            
            self.logger.info("WebSocket connection started")
            
        except Exception as e:
            self.logger.error(f"Error starting WebSocket: {e}")
    
    def stop_websocket(self):
        """Stop WebSocket connection."""
        self._running = False
        if self.ws:
            try:
                self.ws.close()
            except Exception as e:
                self.logger.error(f"Error closing WebSocket: {e}")
        self.ws_connected = False
    
    def _on_ws_connect(self):
        """Handle WebSocket connection."""
        self.ws_connected = True
        self.logger.info("WebSocket connected")
        
        for instrument_token in self.stores.keys():
            try:
                self.ws.subscribe([int(instrument_token)])
            except Exception as e:
                self.logger.error(f"Error subscribing to {instrument_token}: {e}")
    
    def _on_ws_message(self, message):
        """Handle WebSocket message (tick data)."""
        try:
            if 'tick' in message:
                tick = message['tick']
                instrument_token = str(tick['instrument_token'])
                
                if instrument_token not in self.stores:
                    return
                
                timestamp = datetime.now()
                ltp = tick.get('last_price', 0)
                volume = tick.get('volume', 1)
                
                self._process_tick(instrument_token, timestamp, ltp, volume)
                
        except Exception as e:
            self.logger.error(f"Error processing WebSocket message: {e}")
    
    def _on_ws_close(self):
        """Handle WebSocket close."""
        self.ws_connected = False
        self.logger.warning("WebSocket closed")
    
    def _on_ws_error(self, error):
        """Handle WebSocket error."""
        self.logger.error(f"WebSocket error: {error}")
    
    def _process_tick(self, instrument_token: str, timestamp: datetime,
                     price: float, volume: int):
        """Process a tick and update all timeframe candles."""
        with self._lock:
            if instrument_token not in self.stores:
                return
            
            for timeframe, store in self.stores[instrument_token].items():
                completed_candle = store.add_tick(timestamp, price, volume)
                
                if completed_candle:
                    for callback in self._callbacks[instrument_token]:
                        try:
                            callback(instrument_token, completed_candle)
                        except Exception as e:
                            self.logger.error(f"Error in callback: {e}")
    
    def get_dataframe(self, instrument_token: str, timeframe: str) -> Optional[pd.DataFrame]:
        """Get DataFrame for specific instrument and timeframe.
        
        Args:
            instrument_token: Kite instrument token
            timeframe: Timeframe string (e.g., '5min')
        
        Returns:
            DataFrame or None if not available
        """
        with self._lock:
            if (instrument_token not in self.stores or 
                timeframe not in self.stores[instrument_token]):
                return None
            
            return self.stores[instrument_token][timeframe].get_dataframe()
    
    def get_last_n_candles(self, instrument_token: str, timeframe: str,
                          n: int) -> Optional[pd.DataFrame]:
        """Get last N candles for instrument and timeframe.
        
        Args:
            instrument_token: Kite instrument token
            timeframe: Timeframe string
            n: Number of candles
        
        Returns:
            DataFrame or None if not available
        """
        with self._lock:
            if (instrument_token not in self.stores or 
                timeframe not in self.stores[instrument_token]):
                return None
            
            return self.stores[instrument_token][timeframe].get_last_n_candles(n)
    
    def get_current_candle(self, instrument_token: str,
                          timeframe: str) -> Optional[Dict]:
        """Get current incomplete candle.
        
        Args:
            instrument_token: Kite instrument token
            timeframe: Timeframe string
        
        Returns:
            Current candle data or None
        """
        with self._lock:
            if (instrument_token not in self.stores or 
                timeframe not in self.stores[instrument_token]):
                return None
            
            return self.stores[instrument_token][timeframe].get_current_candle()
    
    def get_all_timeframes(self, instrument_token: str) -> Dict[str, pd.DataFrame]:
        """Get DataFrames for all subscribed timeframes.
        
        Args:
            instrument_token: Kite instrument token
        
        Returns:
            Dictionary mapping timeframe -> DataFrame
        """
        result = {}
        with self._lock:
            if instrument_token in self.stores:
                for timeframe, store in self.stores[instrument_token].items():
                    result[timeframe] = store.get_dataframe()
        
        return result
    
    def get_candle_count(self, instrument_token: str, timeframe: str) -> int:
        """Get number of candles available."""
        with self._lock:
            if (instrument_token not in self.stores or 
                timeframe not in self.stores[instrument_token]):
                return 0
            
            return len(self.stores[instrument_token][timeframe].candles)
    
    def clear_data(self, instrument_token: str, timeframe: Optional[str] = None):
        """Clear data for instrument.
        
        Args:
            instrument_token: Kite instrument token
            timeframe: Specific timeframe to clear (all if None)
        """
        with self._lock:
            if instrument_token not in self.stores:
                return
            
            if timeframe is None:
                del self.stores[instrument_token]
                self.logger.info(f"Cleared all data for {instrument_token}")
            elif timeframe in self.stores[instrument_token]:
                del self.stores[instrument_token][timeframe]
                self.logger.info(f"Cleared {timeframe} data for {instrument_token}")
