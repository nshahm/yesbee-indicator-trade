"""Smart cache manager for historical data with date range coverage checking."""

import logging
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pandas as pd

logger = logging.getLogger(__name__)


class DateRangeCache:
    """Manages cached data with awareness of date coverage."""
    
    def __init__(self, cache_dir: str = "history_data"):
        """Initialize the cache manager.
        
        Args:
            cache_dir: Directory where cached data is stored
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"DateRangeCache initialized with cache dir: {self.cache_dir}")
    
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
    
    def _extract_date_range_from_filename(self, filename: str) -> Optional[Tuple[datetime, datetime]]:
        """Extract date range from cache filename.
        
        Args:
            filename: Cache filename
        
        Returns:
            Tuple of (from_date, to_date) or None if invalid format
        """
        try:
            parts = filename.replace('.json', '').split('_')
            if len(parts) >= 3:
                from_str = parts[-2]
                to_str = parts[-1]
                
                if len(from_str) == 12 and len(to_str) == 12:
                    from_date = datetime.strptime(from_str, '%Y%m%d%H%M')
                    to_date = datetime.strptime(to_str, '%Y%m%d%H%M')
                    return from_date, to_date
        except Exception as e:
            logger.debug(f"Could not extract date range from filename {filename}: {e}")
        
        return None
    
    def get_cached_files_for_instrument(self, instrument_token: str, 
                                       interval: str, 
                                       index_name: Optional[str] = None) -> List[Tuple[Path, datetime, datetime]]:
        """Get all cached files for an instrument and interval, extracting date ranges.
        
        Args:
            instrument_token: Kite instrument token
            interval: Kite interval format
            index_name: Optional index name to filter by prefix
        
        Returns:
            List of (file_path, from_date, to_date) tuples
        """
        if index_name:
            pattern = f"{index_name}_{instrument_token}_{interval}_*.json"
        else:
            pattern = f"{instrument_token}_{interval}_*.json"
        files = list(self.cache_dir.glob(pattern))
        
        cached_files = []
        for file in files:
            date_range = self._extract_date_range_from_filename(file.name)
            if date_range:
                cached_files.append((file, date_range[0], date_range[1]))
        
        cached_files.sort(key=lambda x: x[1])
        return cached_files
    
    def get_data_coverage(self, instrument_token: str, interval: str, 
                         index_name: Optional[str] = None) -> List[Tuple[datetime, datetime]]:
        """Get list of date ranges that are covered by cached data.
        
        Args:
            instrument_token: Kite instrument token
            interval: Kite interval format
            index_name: Optional index name to filter by prefix
        
        Returns:
            List of (from_date, to_date) tuples sorted by date
        """
        cached_files = self.get_cached_files_for_instrument(instrument_token, interval, index_name)
        coverage = [(f[1], f[2]) for f in cached_files]
        return coverage
    
    def check_date_coverage(self, instrument_token: str, interval: str,
                           from_date: datetime, to_date: datetime, 
                           index_name: Optional[str] = None) -> Tuple[bool, List[Tuple[datetime, datetime]]]:
        """Check if requested date range is fully covered by cache.
        
        Args:
            instrument_token: Kite instrument token
            interval: Kite interval format
            from_date: Requested start date
            to_date: Requested end date
            index_name: Optional index name to filter by prefix
        
        Returns:
            Tuple of (is_fully_covered, missing_ranges)
            - is_fully_covered: True if full range is in cache
            - missing_ranges: List of (start, end) date ranges that need to be fetched
        """
        cached_files = self.get_cached_files_for_instrument(instrument_token, interval, index_name)
        
        if not cached_files:
            logger.info(f"No cache found for {instrument_token} {interval}")
            return False, [(from_date, to_date)]
        
        logger.debug(f"Found {len(cached_files)} cached files for {instrument_token} {interval}")
        for file, file_from, file_to in cached_files:
            logger.debug(f"  Cache: {file_from.strftime('%Y-%m-%d %H:%M')} to {file_to.strftime('%Y-%m-%d %H:%M')}")
        
        missing_ranges = []
        current_date = from_date
        
        for file_path, cache_from, cache_to in cached_files:
            if cache_from > current_date:
                gap = (current_date, cache_from)
                missing_ranges.append(gap)
                logger.debug(f"Missing data: {gap[0].strftime('%Y-%m-%d %H:%M')} to {gap[1].strftime('%Y-%m-%d %H:%M')}")
            
            if cache_to >= current_date:
                current_date = max(current_date, cache_to + timedelta(minutes=1))
        
        if current_date < to_date:
            gap = (current_date, to_date)
            missing_ranges.append(gap)
            logger.debug(f"Missing data: {gap[0].strftime('%Y-%m-%d %H:%M')} to {gap[1].strftime('%Y-%m-%d %H:%M')}")
        
        is_fully_covered = len(missing_ranges) == 0
        return is_fully_covered, missing_ranges
    
    def load_cached_data(self, instrument_token: str, interval: str,
                        from_date: datetime, to_date: datetime, 
                        index_name: Optional[str] = None) -> Optional[pd.DataFrame]:
        """Load cached data for a date range.
        
        Args:
            instrument_token: Kite instrument token
            interval: Kite interval format
            from_date: Requested start date
            to_date: Requested end date
            index_name: Optional index name to filter by prefix
        
        Returns:
            DataFrame with cached data, or None if partial/no data available
        """
        cached_files = self.get_cached_files_for_instrument(instrument_token, interval, index_name)
        
        if not cached_files:
            return None
        
        all_data = []
        
        for file_path, cache_from, cache_to in cached_files:
            if cache_to < from_date or cache_from > to_date:
                continue
            
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                all_data.extend(data)
                logger.info(f"Loaded {len(data)} candles from {file_path.name}")
            except Exception as e:
                logger.error(f"Error loading cache file {file_path}: {e}")
        
        if not all_data:
            return None
        
        df = pd.DataFrame(all_data)
        
        try:
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
                df.set_index('date', inplace=True)
            
            df = df.sort_index()
            df = df[~df.index.duplicated(keep='first')]
            
            from_date_filter = from_date
            to_date_filter = to_date
            
            if df.index.tz is not None:
                if from_date_filter.tzinfo is None:
                    from_date_filter = from_date_filter.replace(tzinfo=df.index.tz)
                if to_date_filter.tzinfo is None:
                    to_date_filter = to_date_filter.replace(tzinfo=df.index.tz)
            
            df_filtered = df[(df.index >= from_date_filter) & (df.index <= to_date_filter)]
            
            if not df_filtered.empty:
                logger.info(f"Loaded {len(df_filtered)} candles from cache for {from_date} to {to_date}")
                return df_filtered[['open', 'high', 'low', 'close', 'volume']]
        except Exception as e:
            logger.error(f"Error processing cached data: {e}")
        
        return None
    
    def save_data_to_cache(self, instrument_token: str, interval: str,
                          from_date: datetime, to_date: datetime,
                          data: List[Dict], index_name: Optional[str] = None) -> bool:
        """Save data to cache.
        
        Args:
            instrument_token: Kite instrument token
            interval: Kite interval format
            from_date: Start date
            to_date: End date
            data: List of candle data to cache
            index_name: Optional index name to use in filename prefix
        
        Returns:
            True if successful, False otherwise
        """
        if not data:
            logger.warning("No data to cache")
            return False
        
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
            
            cache_file = self._get_cache_file_path(instrument_token, interval, from_date, to_date, index_name)
            
            with open(cache_file, 'w') as f:
                json.dump(serializable_data, f)
            
            logger.info(f"Cached {len(data)} candles to {cache_file.name}")
            return True
        except Exception as e:
            logger.error(f"Error saving cache file: {e}")
            return False
    
    def list_all_cache_files(self) -> List[Dict]:
        """List all cache files with their details.
        
        Returns:
            List of dicts with file info
        """
        files_info = []
        
        for file in self.cache_dir.glob("*.json"):
            try:
                date_range = self._extract_date_range_from_filename(file.name)
                if date_range:
                    files_info.append({
                        'filename': file.name,
                        'from_date': date_range[0],
                        'to_date': date_range[1],
                        'file_size': file.stat().st_size,
                        'modified': datetime.fromtimestamp(file.stat().st_mtime)
                    })
            except Exception as e:
                logger.debug(f"Error processing file {file.name}: {e}")
        
        files_info.sort(key=lambda x: x['from_date'])
        return files_info
    
    def clear_cache(self, instrument_token: str = None, 
                   before_date: datetime = None) -> int:
        """Clear cache files.
        
        Args:
            instrument_token: Clear files for specific instrument only (optional)
            before_date: Clear files modified before this date (optional)
        
        Returns:
            Number of files deleted
        """
        pattern = f"{instrument_token}_*.json" if instrument_token else "*.json"
        files = list(self.cache_dir.glob(pattern))
        
        deleted_count = 0
        for file in files:
            should_delete = True
            
            if before_date:
                file_mtime = datetime.fromtimestamp(file.stat().st_mtime)
                should_delete = file_mtime < before_date
            
            if should_delete:
                try:
                    file.unlink()
                    logger.info(f"Deleted cache file: {file.name}")
                    deleted_count += 1
                except Exception as e:
                    logger.error(f"Error deleting file {file}: {e}")
        
        return deleted_count
