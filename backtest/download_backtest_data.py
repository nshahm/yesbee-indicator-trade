#!/usr/bin/env python3
"""Download historical index data for backtesting from Kite API.

Reads index configuration from config/options.yaml and date range from config/backtest.yaml,
then downloads OHLCV data for enabled indices across specified timeframes.

Usage:
    python backtest/download_backtest_data.py                    # Uses default configs
    python backtest/download_backtest_data.py --backtest-config config/backtest.yaml
    python backtest/download_backtest_data.py --options-config config/options.yaml
    python backtest/download_backtest_data.py --timeframes 5m,15m,1h
"""

import logging
import sys
import argparse
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BacktestDataDownloader:
    """Download historical data for backtest indices."""
    
    # Default tokens as fallback
    INDEX_TOKENS = {
        'NIFTY50': '256265',
        'BANKNIFTY': '260105',
        'FINNIFTY': '257801',
        'NIFTY_IT': '257801',
        'NIFTY_BANK': '257864',
        'NIFTY_FINANCE': '257865',
        'NIFTY_FMCG': '257870',
        'NIFTY_AUTO': '257868',
        'NIFTY_METAL': '257866',
        'NIFTY_PHARMA': '257872',
        'NIFTY_REALTY': '257873',
        'NIFTY_ENERGY': '257869',
        'NIFTY_INFRA': '257871',
        'SENSEX': '256355',
    }
    
    INTERVAL_MAPPING = {
        '1m': '1minute',
        '3m': '3minute',
        '5m': '5minute',
        '15m': '15minute',
        '30m': '30minute',
        '1h': '60minute',
        'daily': 'day',
        'day': 'day',
    }
    
    def __init__(self, backtest_config_path: str = 'config/backtest.yaml',
                 options_config_path: str = 'config/options.yaml',
                 kite_config_path: str = 'config/kite-config.yaml'):
        """Initialize downloader with config files.
        
        Args:
            backtest_config_path: Path to backtest.yaml
            options_config_path: Path to options.yaml
            kite_config_path: Path to kite-config.yaml
        """
        self.backtest_config = self._load_yaml(backtest_config_path)
        self.options_config = self._load_yaml(options_config_path)
        self.kite_config = self._load_yaml(kite_config_path)
        self._merge_kite_tokens()
        
        self.kite_broker = None
        self.historical_fetcher = None
        self._initialize_kite()
    
    def _load_yaml(self, filepath: str) -> Dict:
        """Load YAML configuration file.
        
        Args:
            filepath: Path to YAML file
            
        Returns:
            Parsed YAML as dictionary
        """
        try:
            with open(filepath, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.debug(f"Config file not found: {filepath}")
            return {}
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML {filepath}: {e}")
            return {}
            
    def _merge_kite_tokens(self):
        """Merge tokens from kite-config.yaml into INDEX_TOKENS."""
        if not self.kite_config:
            return
            
        try:
            indices = self.kite_config.get('kite', {}).get('instruments', {}).get('indices', {})
            for symbol, info in indices.items():
                token = info.get('token')
                if token:
                    self.INDEX_TOKENS[symbol.upper()] = str(token)
                    logger.debug(f"Loaded token for {symbol}: {token}")
        except Exception as e:
            logger.warning(f"Error merging tokens from kite-config: {e}")
    
    def _initialize_kite(self):
        """Initialize Kite API connection."""
        try:
            from broker.kite.kite_connect import KiteConnectBroker
            from broker.kite.historical_data_fetcher import HistoricalDataFetcher
            
            self.kite_broker = KiteConnectBroker()
            if self.kite_broker.is_connected():
                cache_dir = self.backtest_config.get('backtest', {}).get(
                    'kite_api', {}
                ).get('cache_dir', 'history_data')
                
                self.historical_fetcher = HistoricalDataFetcher(
                    self.kite_broker.kite,
                    cache_dir=cache_dir
                )
                logger.info("✓ Connected to Kite API")
            else:
                logger.warning("Failed to connect to Kite API - check credentials")
                self.kite_broker = None
        except Exception as e:
            logger.error(f"Error initializing Kite connection: {e}")
            self.kite_broker = None
    
    def get_enabled_indices(self) -> Dict[str, str]:
        """Get enabled indices from options.yaml.
        
        Returns:
            Dictionary of {symbol: description} for enabled indices
        """
        indices = {}
        
        if not self.options_config:
            logger.warning("Options config not loaded, using default indices")
            return {'NIFTY50': 'Nifty 50'}
        
        indices_config = self.options_config.get('indices', {})
        
        for index_key, index_config in indices_config.items():
            if index_config.get('enabled', False):
                symbol = index_config.get('symbol', '').upper()
                description = index_config.get('description', '')
                if symbol:
                    indices[symbol] = description
        
        if not indices:
            logger.warning("No enabled indices found in options.yaml")
            logger.info("Using default: NIFTY50")
            indices['NIFTY50'] = 'Nifty 50 Index'
        
        return indices
    
    def get_date_range(self) -> tuple:
        """Parse date range from backtest.yaml.
        
        Returns:
            (from_date, to_date) as datetime objects
        """
        backtest_config = self.backtest_config.get('backtest', {})
        date_range_str = backtest_config.get('date_range', '')
        
        if not date_range_str or '_' not in date_range_str:
            logger.warning("Invalid date_range format in backtest.yaml")
            from_date = datetime(2025, 1, 1, 9, 15)
            to_date = datetime.now()
        else:
            try:
                from_str, to_str = date_range_str.split('_')
                from_date = datetime.strptime(from_str, '%Y%m%d%H%M')
                to_date = datetime.strptime(to_str, '%Y%m%d%H%M')
            except ValueError as e:
                logger.error(f"Error parsing date_range: {e}")
                from_date = datetime(2025, 1, 1, 9, 15)
                to_date = datetime.now()
        
        logger.info(f"Date range: {from_date} to {to_date}")
        return from_date, to_date
    
    def get_timeframes(self) -> List[str]:
        """Get timeframes to download from backtest.yaml.
        
        Returns:
            List of Kite API interval format strings
        """
        backtest_config = self.backtest_config.get('backtest', {})
        kite_api_config = backtest_config.get('kite_api', {})
        timeframe_list = kite_api_config.get('timeframes', [])
        
        if not timeframe_list:
            logger.warning("No timeframes configured, using defaults")
            timeframe_list = ['5minute', '15minute', '60minute']
        
        logger.info(f"Timeframes to download: {timeframe_list}")
        return timeframe_list
    
    def download_index_data(self, indices: Optional[Dict[str, str]] = None,
                           from_date: Optional[datetime] = None,
                           to_date: Optional[datetime] = None,
                           timeframes: Optional[List[str]] = None) -> bool:
        """Download data for specified indices.
        
        Args:
            indices: Dict of {symbol: description}. If None, uses enabled indices from config
            from_date: Start date. If None, uses config
            to_date: End date. If None, uses config
            timeframes: List of Kite intervals. If None, uses config
            
        Returns:
            True if all downloads successful, False otherwise
        """
        if not self.historical_fetcher:
            logger.error("❌ Kite API not connected. Cannot download data.")
            return False
        
        if indices is None:
            indices = self.get_enabled_indices()
        if from_date is None or to_date is None:
            from_date, to_date = self.get_date_range()
        if timeframes is None:
            timeframes = self.get_timeframes()
        
        total_downloads = len(indices) * len(timeframes)
        completed = 0
        failed = 0
        
        logger.info(f"\n{'='*70}")
        logger.info(f"BACKTEST DATA DOWNLOAD")
        logger.info(f"{'='*70}")
        logger.info(f"Indices: {len(indices)}")
        logger.info(f"Timeframes: {len(timeframes)}")
        logger.info(f"Total downloads: {total_downloads}")
        logger.info(f"{'='*70}\n")
        
        for symbol, description in indices.items():
            logger.info(f"\n📊 {symbol} ({description})")
            logger.info(f"{'─'*70}")
            
            if symbol not in self.INDEX_TOKENS:
                logger.warning(f"⚠️  Token not found for {symbol}, skipping")
                continue
            
            token = self.INDEX_TOKENS[symbol]
            
            for interval in timeframes:
                try:
                    logger.info(f"  ⏳ Fetching {interval}...")
                    
                    df = self.historical_fetcher.fetch_historical_data(
                        instrument_token=token,
                        interval=interval,
                        from_date=from_date,
                        to_date=to_date,
                        use_cache=True,
                        index_name=symbol.lower()
                    )
                    
                    if df is not None and not df.empty:
                        logger.info(f"     ✓ {len(df)} candles")
                        completed += 1
                    else:
                        logger.warning(f"     ⚠️  No data returned")
                        failed += 1
                
                except Exception as e:
                    logger.error(f"     ❌ Error: {e}")
                    failed += 1
        
        logger.info(f"\n{'='*70}")
        logger.info(f"DOWNLOAD SUMMARY")
        logger.info(f"{'='*70}")
        logger.info(f"Completed: {completed}/{total_downloads}")
        logger.info(f"Failed: {failed}/{total_downloads}")
        logger.info(f"Success rate: {(completed/total_downloads*100):.1f}%")
        logger.info(f"{'='*70}\n")
        
        return failed == 0
    
    def list_downloaded_files(self):
        """List all downloaded cached data files."""
        if not self.historical_fetcher:
            logger.warning("Kite API not connected")
            return
        
        cache_dir = Path(self.historical_fetcher.cache_dir)
        
        if not cache_dir.exists():
            logger.info("No cached data directory found")
            return
        
        json_files = sorted(
            cache_dir.glob('*.json'),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )
        
        if not json_files:
            logger.info("No cached data files found")
            return
        
        logger.info(f"\n{'='*70}")
        logger.info(f"CACHED DATA FILES ({len(json_files)} total)")
        logger.info(f"{'='*70}")
        
        total_size = 0
        for file in json_files:
            size_mb = file.stat().st_size / (1024 * 1024)
            total_size += file.stat().st_size
            mtime = datetime.fromtimestamp(file.stat().st_mtime)
            logger.info(f"{file.name:<60} {size_mb:>8.2f} MB  {mtime}")
        
        logger.info(f"{'='*70}")
        logger.info(f"Total cached: {total_size / (1024*1024):.2f} MB")
        logger.info(f"{'='*70}\n")


def main():
    parser = argparse.ArgumentParser(
        description='Download historical index data for backtesting',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python backtest/download_backtest_data.py                    # Uses default configs
  python backtest/download_backtest_data.py --list-only        # List cached files only
  python backtest/download_backtest_data.py --indices NIFTY50,BANKNIFTY
  python backtest/download_backtest_data.py --timeframes 5m,15m,1h
        '''
    )
    
    parser.add_argument('--backtest-config', default='config/backtest.yaml',
                        help='Path to backtest.yaml')
    parser.add_argument('--options-config', default='config/options.yaml',
                        help='Path to options.yaml')
    parser.add_argument('--kite-config', default='config/kite-config.yaml',
                        help='Path to kite-config.yaml')
    parser.add_argument('--indices', type=str,
                        help='Comma-separated list of indices (e.g., NIFTY50,BANKNIFTY)')
    parser.add_argument('--timeframes', type=str,
                        help='Comma-separated timeframes (e.g., 5m,15m,1h)')
    parser.add_argument('--from-date', type=str,
                        help='Start date (YYYYMMDDHHMM format)')
    parser.add_argument('--to-date', type=str,
                        help='End date (YYYYMMDDHHMM format)')
    parser.add_argument('--list-only', action='store_true',
                        help='Only list cached files, do not download')
    
    args = parser.parse_args()
    
    downloader = BacktestDataDownloader(
        backtest_config_path=args.backtest_config,
        options_config_path=args.options_config,
        kite_config_path=args.kite_config
    )
    
    if args.list_only:
        downloader.list_downloaded_files()
        return 0
    
    indices = None
    if args.indices:
        indices = {sym.strip().upper(): '' for sym in args.indices.split(',')}
    
    timeframes = None
    if args.timeframes:
        timeframes = []
        for tf in args.timeframes.split(','):
            tf = tf.strip().lower()
            if tf in downloader.INTERVAL_MAPPING:
                timeframes.append(downloader.INTERVAL_MAPPING[tf])
            else:
                logger.warning(f"Unknown timeframe: {tf}")
    
    from_date = None
    to_date = None
    if args.from_date:
        try:
            from_date = datetime.strptime(args.from_date, '%Y%m%d%H%M')
        except ValueError:
            logger.error(f"Invalid from_date format: {args.from_date}")
            return 1
    if args.to_date:
        try:
            to_date = datetime.strptime(args.to_date, '%Y%m%d%H%M')
        except ValueError:
            logger.error(f"Invalid to_date format: {args.to_date}")
            return 1
    
    success = downloader.download_index_data(
        indices=indices,
        from_date=from_date,
        to_date=to_date,
        timeframes=timeframes
    )
    
    downloader.list_downloaded_files()
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
