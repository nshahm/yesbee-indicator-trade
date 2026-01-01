"""Historical data fetcher from Kite API with caching and 100-day limit handling."""

import logging
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pandas as pd
from kiteconnect import KiteConnect

from broker.kite.cache_manager import DateRangeCache

logger = logging.getLogger(__name__)


class HistoricalDataFetcher:
    """Fetch historical data from Kite API with chunked calls and caching."""
    
    MAX_DAYS_PER_CALL = 100
    
    def __init__(self, kite_client: Optional[KiteConnect], cache_dir: str = "history_data"):
        """Initialize the fetcher.
        
        Args:
            kite_client: Initialized KiteConnect instance or None
            cache_dir: Directory to cache downloaded data
        """
        self.kite = kite_client
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_manager = DateRangeCache(cache_dir)
        logger.info(f"Historical data fetcher initialized. Cache dir: {self.cache_dir}")
    
    def _get_cache_file_path(self, instrument_token: str, interval: str, 
                            from_date: datetime, to_date: datetime, 
                            index_name: Optional[str] = None) -> Path:
        """Generate cache file path based on instrument, interval, and date range.
        
        Args:
            instrument_token: Kite instrument token
            interval: Kite interval format (1minute, 5minute, 15minute, etc.)
            from_date: Start date
            to_date: End date
            index_name: Optional index name prefix (e.g., 'nifty50', 'banknifty')
        
        Returns:
            Path to cache file
        """
        from_str = from_date.strftime("%Y%m%d%H%M")
        to_str = to_date.strftime("%Y%m%d%H%M")
        if index_name:
            filename = f"{index_name}_{instrument_token}_{interval}_{from_str}_{to_str}.json"
        else:
            filename = f"{instrument_token}_{interval}_{from_str}_{to_str}.json"
        return self.cache_dir / filename
    
    def _load_from_cache(self, cache_file: Path) -> Optional[List[List]]:
        """Load data from cache file.
        
        Args:
            cache_file: Path to cache file
        
        Returns:
            List of candle data or None if file doesn't exist
        """
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, 'r') as f:
                data = json.load(f)
            logger.info(f"Loaded {len(data)} candles from cache: {cache_file.name}")
            return data
        except Exception as e:
            logger.error(f"Error loading cache file {cache_file}: {e}")
            return None
    
    def _save_to_cache(self, cache_file: Path, data: List) -> bool:
        """Save data to cache file.
        
        Args:
            cache_file: Path to cache file
            data: List of candle data to cache
        
        Returns:
            True if successful, False otherwise
        """
        try:
            serializable_data = []
            for candle in data:
                if isinstance(candle, dict):
                    candle_copy = candle.copy()
                    if 'date' in candle_copy and hasattr(candle_copy['date'], 'isoformat'):
                        candle_copy['date'] = candle_copy['date'].isoformat()
                    serializable_data.append(candle_copy)
                else:
                    serializable_data.append(candle)
            
            with open(cache_file, 'w') as f:
                json.dump(serializable_data, f)
            logger.info(f"Cached {len(data)} candles to: {cache_file.name}")
            return True
        except Exception as e:
            logger.error(f"Error saving cache file {cache_file}: {e}")
            return False
    
    def _fetch_chunk(self, instrument_token: str, interval: str,
                    from_date: datetime, to_date: datetime) -> Optional[List[List]]:
        """Fetch a single chunk of data from Kite API.
        
        Args:
            instrument_token: Kite instrument token
            interval: Kite interval format
            from_date: Start date for this chunk
            to_date: End date for this chunk
        
        Returns:
            List of candle data or None if failed
        """
        try:
            if not self.kite:
                logger.error("Kite client not initialized. Cannot fetch data from API.")
                return None
                
            logger.info(
                f"Fetching {instrument_token} {interval} "
                f"from {from_date.strftime('%Y-%m-%d %H:%M')} "
                f"to {to_date.strftime('%Y-%m-%d %H:%M')}"
            )
            
            data = self.kite.historical_data(
                instrument_token=instrument_token,
                from_date=from_date,
                to_date=to_date,
                interval=interval
            )
            
            if data:
                logger.info(f"Received {len(data)} candles from API")
            else:
                logger.warning(f"No data received from API for {from_date} to {to_date}")
            
            return data if data else []
            
        except Exception as e:
            logger.error(f"Error fetching data from API: {e}", exc_info=True)
            return None
    
    def _calculate_chunks(self, from_date: datetime, to_date: datetime) -> List[Tuple[datetime, datetime]]:
        """Calculate date chunks for API calls (max 100 days per call).
        
        Args:
            from_date: Overall start date
            to_date: Overall end date
        
        Returns:
            List of (chunk_start, chunk_end) tuples
        """
        chunks = []
        current_start = from_date
        
        while current_start < to_date:
            chunk_end = min(
                current_start + timedelta(days=self.MAX_DAYS_PER_CALL),
                to_date
            )
            chunks.append((current_start, chunk_end))
            current_start = chunk_end
        
        logger.info(f"Data range split into {len(chunks)} chunk(s) of max {self.MAX_DAYS_PER_CALL} days")
        return chunks
    
    def fetch_historical_data(self, instrument_token: str, interval: str,
                             from_date: datetime, to_date: datetime,
                             use_cache: bool = True, index_name: Optional[str] = None) -> Optional[pd.DataFrame]:
        """Fetch historical data with smart caching - NO API calls if data is cached.
        
        Priority:
        1. Check cache FIRST - if fully cached, load and return (NO API connection)
        2. If partially cached - load partial data
        3. Only connect to Kite API if missing data needs to be fetched
        4. Merge cached + fetched data and save
        
        All merged files are kept permanently for reuse on subsequent runs.
        
        Args:
            instrument_token: Kite instrument token (e.g., 'NSE:NIFTY50')
            interval: Kite interval format (1minute, 5minute, 15minute, etc.)
            from_date: Start date
            to_date: End date
            use_cache: Whether to use/save cache (default: True)
            index_name: Optional index name for cache filename prefix
        
        Returns:
            DataFrame with OHLCV data indexed by date, or None if failed
        """
        logger.info(f"Loading data for {instrument_token} {interval}")
        logger.info(f"Date range: {from_date.strftime('%Y-%m-%d %H:%M')} to {to_date.strftime('%Y-%m-%d %H:%M')}")
        
        total_days = (to_date - from_date).days
        logger.info(f"Duration: {total_days} days")
        
        cached_df = None
        needs_api_fetch = False
        missing_ranges = []
        
        if use_cache:
            logger.info("→ Checking cache for available data...")
            is_fully_covered, missing_ranges = self.cache_manager.check_date_coverage(
                instrument_token, interval, from_date, to_date, index_name
            )
            
            if is_fully_covered:
                logger.info("✓ Data is fully cached. Loading from cache (NO API connection)...")
                cached_df = self.cache_manager.load_cached_data(
                    instrument_token, interval, from_date, to_date, index_name
                )
                if cached_df is not None and not cached_df.empty:
                    logger.info(f"✓ SUCCESS: Loaded {len(cached_df)} candles from cache")
                    logger.info(f"✓ NO API calls needed - data available locally")
                    return cached_df
            else:
                logger.info(f"→ Cache has partial data. Found {len(missing_ranges)} missing date range(s):")
                for i, (miss_from, miss_to) in enumerate(missing_ranges, 1):
                    logger.info(f"  {i}. Missing: {miss_from.strftime('%Y-%m-%d %H:%M')} to {miss_to.strftime('%Y-%m-%d %H:%M')}")
                
                cached_df = self.cache_manager.load_cached_data(
                    instrument_token, interval, from_date, to_date, index_name
                )
                if cached_df is not None and not cached_df.empty:
                    logger.info(f"✓ Loaded {len(cached_df)} candles from partial cache")
                
                needs_api_fetch = True
        else:
            needs_api_fetch = True
        
        all_data = []
        
        if needs_api_fetch:
            logger.info("→ Fetching missing data from Kite API...")
            chunks = self._calculate_chunks(from_date, to_date)
            logger.info(f"  Will make {len(chunks)} API call(s) to fetch missing data")
            
            for idx, (chunk_start, chunk_end) in enumerate(chunks, 1):
                logger.info(f"  Fetching chunk {idx}/{len(chunks)}: {chunk_start.strftime('%Y-%m-%d %H:%M')} to {chunk_end.strftime('%Y-%m-%d %H:%M')}")
                
                chunk_data = self._fetch_chunk(
                    instrument_token, interval, chunk_start, chunk_end
                )
                
                if chunk_data is None:
                    logger.error(f"Failed to fetch chunk {idx}/{len(chunks)}")
                    if cached_df is not None and not cached_df.empty:
                        logger.warning("API fetch failed. Returning available cached data")
                        return cached_df
                    return None
                
                if chunk_data:
                    all_data.extend(chunk_data)
                    logger.info(f"  Chunk {idx}: {len(chunk_data)} candles (total fetched: {len(all_data)})")
            
            if not all_data:
                if cached_df is not None and not cached_df.empty:
                    logger.info(f"No new data fetched from API. Using cached data: {len(cached_df)} candles")
                    return cached_df
                logger.warning(f"Failed to fetch data from API for {instrument_token} {interval}")
                return None
            
            logger.info(f"✓ Successfully fetched {len(all_data)} candles from API")
        
        if use_cache and all_data:
            merged_df = self._convert_to_dataframe(all_data)
            
            if cached_df is not None and not cached_df.empty:
                logger.info(f"→ Merging {len(cached_df)} cached candles with {len(merged_df)} newly fetched candles")
                merged_df = pd.concat([cached_df, merged_df])
                merged_df = merged_df.drop_duplicates(subset=['open', 'high', 'low', 'close', 'volume'], keep='first')
                merged_df = merged_df.sort_index()
                logger.info(f"✓ Merged dataset: {len(merged_df)} total candles")
            
            all_data_for_cache = []
            for idx, row in merged_df.iterrows():
                all_data_for_cache.append({
                    'date': idx.isoformat() if hasattr(idx, 'isoformat') else str(idx),
                    'open': float(row['open']),
                    'high': float(row['high']),
                    'low': float(row['low']),
                    'close': float(row['close']),
                    'volume': int(row['volume'])
                })
            
            self._save_to_cache(self._get_cache_file_path(
                instrument_token, interval, from_date, to_date, index_name
            ), all_data_for_cache)
            logger.info(f"✓ Saved merged cache file for {from_date.strftime('%Y-%m-%d %H:%M')} to {to_date.strftime('%Y-%m-%d %H:%M')}")
            logger.info("✓ Cache file will be reused on next run with same/overlapping date range (no API call)")
            
            return merged_df
        
        if all_data:
            return self._convert_to_dataframe(all_data)
        
        return cached_df if cached_df is not None else None
    
    def _convert_to_dataframe(self, data: List) -> pd.DataFrame:
        """Convert Kite API data to DataFrame.
        
        Args:
            data: List of candle data from Kite API (can be dicts or tuples)
        
        Returns:
            DataFrame with OHLCV columns
        """
        if not data:
            return pd.DataFrame(columns=['date', 'open', 'high', 'low', 'close', 'volume'])
        
        processed_data = []
        for candle in data:
            if isinstance(candle, dict):
                processed_data.append({
                    'date': candle.get('date'),
                    'open': float(candle.get('open', 0)),
                    'high': float(candle.get('high', 0)),
                    'low': float(candle.get('low', 0)),
                    'close': float(candle.get('close', 0)),
                    'volume': int(candle.get('volume', 0)),
                    'oi': int(candle.get('oi', 0)),
                })
            else:
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
        df = df.sort_index()
        
        return df[['open', 'high', 'low', 'close', 'volume']]
    
    def fetch_multiple_timeframes(self, instrument_token: str, intervals: List[str],
                                 from_date: datetime, to_date: datetime) -> Dict[str, pd.DataFrame]:
        """Fetch historical data for multiple timeframes.
        
        Args:
            instrument_token: Kite instrument token
            intervals: List of Kite interval formats
            from_date: Start date
            to_date: End date
        
        Returns:
            Dictionary mapping interval -> DataFrame
        """
        result = {}
        
        for interval in intervals:
            try:
                df = self.fetch_historical_data(
                    instrument_token, interval, from_date, to_date
                )
                if df is not None:
                    result[interval] = df
                else:
                    logger.warning(f"Failed to fetch {interval}, skipping")
            except Exception as e:
                logger.error(f"Error fetching {interval}: {e}", exc_info=True)
        
        return result
    
    def get_cached_files(self, instrument_token: str = None) -> List[Path]:
        """Get list of cached data files.
        
        Args:
            instrument_token: Filter by instrument token (optional)
        
        Returns:
            List of cache file paths
        """
        pattern = f"{instrument_token}_*.json" if instrument_token else "*.json"
        files = list(self.cache_dir.glob(pattern))
        files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        return files
    
    def merge_chunk_files(self, instrument_token: str, interval: str, 
                         from_date: datetime, to_date: datetime) -> bool:
        """Merge individual chunk cache files into a single merged file.
        
        This is useful for consolidating previously cached chunks.
        
        Args:
            instrument_token: Instrument token
            interval: Interval format
            from_date: Overall start date
            to_date: Overall end date
        
        Returns:
            True if merge successful, False otherwise
        """
        try:
            all_data = []
            chunks = self._calculate_chunks(from_date, to_date)
            
            for chunk_start, chunk_end in chunks:
                chunk_file = self._get_cache_file_path(
                    instrument_token, interval, chunk_start, chunk_end
                )
                chunk_data = self._load_from_cache(chunk_file)
                if chunk_data:
                    all_data.extend(chunk_data)
                    logger.info(f"Loaded {len(chunk_data)} candles from chunk: {chunk_file.name}")
            
            if not all_data:
                logger.warning("No data found to merge")
                return False
            
            merged_file = self._get_cache_file_path(
                instrument_token, interval, from_date, to_date
            )
            self._save_to_cache(merged_file, all_data)
            logger.info(f"Merged {len(all_data)} candles into: {merged_file.name}")
            
            return True
        except Exception as e:
            logger.error(f"Error merging chunk files: {e}")
            return False
    
    def cleanup_chunk_files(self, instrument_token: str = None) -> int:
        """Clean up individual chunk cache files, keeping only merged files.
        
        Args:
            instrument_token: Clean files for specific instrument only (optional)
        
        Returns:
            Number of files deleted
        """
        import re
        
        pattern = f"{instrument_token}_*.json" if instrument_token else "*.json"
        files = list(self.cache_dir.glob(pattern))
        
        chunk_pattern = re.compile(r'_\d{12}_\d{12}\.json$')
        
        deleted_count = 0
        for file in files:
            if chunk_pattern.search(file.name):
                try:
                    file.unlink()
                    deleted_count += 1
                    logger.info(f"Deleted chunk cache file: {file.name}")
                except Exception as e:
                    logger.error(f"Error deleting cache file {file}: {e}")
        
        return deleted_count
    
    def clear_cache(self, instrument_token: str = None, keep_recent: int = 0) -> int:
        """Clear cache files.
        
        Args:
            instrument_token: Clear files for specific instrument only (optional)
            keep_recent: Keep N most recent files (default: 0, clear all)
        
        Returns:
            Number of files deleted
        """
        files = self.get_cached_files(instrument_token)
        
        if keep_recent > 0:
            files = files[keep_recent:]
        
        deleted_count = 0
        for file in files:
            try:
                file.unlink()
                deleted_count += 1
                logger.info(f"Deleted cache file: {file.name}")
            except Exception as e:
                logger.error(f"Error deleting cache file {file}: {e}")
        
        return deleted_count
