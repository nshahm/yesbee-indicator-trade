"""Market status checker using Zerodha Kite API and Upstox market holidays."""

import logging
from datetime import datetime, time, date
from typing import Dict, Optional, List
from kiteconnect import KiteConnect
import requests

logger = logging.getLogger(__name__)

UPSTOX_HOLIDAYS_API = "https://api.upstox.com/v2/market/holidays"


class MarketStatus:
    """Check if market is open, including holiday and weekend checks."""
    
    MARKET_OPEN_TIME = time(9, 15)
    MARKET_CLOSE_TIME = time(15, 30)
    MARKET_CHECK_TIME = time(9, 0)
    EXCHANGE = 'NSE'
    
    def __init__(self, kite: Optional[KiteConnect] = None):
        """Initialize market status checker.
        
        Args:
            kite: KiteConnect instance. If None, API-dependent features will fail gracefully.
        """
        self.kite = kite
        self._holidays_cache = None
        self._support_market_holidays = self._check_market_holidays_support()
        self._daily_market_status_cache = None
        self._daily_market_status_date = None
        self._api_holidays_cache = None
    
    def check_market_status_at_open(self) -> Dict:
        """
        Check market status at 9am and cache for the entire day.
        This should be called once at market open time (9:00 AM).
        
        Returns:
            Dictionary with market status and caching info
        """
        now = datetime.now()
        today = now.date()
        
        logger.info(f"[MARKET CHECK AT {now.strftime('%H:%M:%S')}] Checking market status for {today}...")
        
        is_weekend = not self._is_weekday(now)
        is_holiday = self._is_holiday(today)
        
        if is_weekend:
            status = 'CLOSED'
            reason = f'Weekend ({now.strftime("%A")})'
            logger.warning(f"[MARKET STATUS] Market is CLOSED - {reason}")
            self._daily_market_status_cache = False
        elif is_holiday:
            holiday_name = self._get_holiday_name(today)
            status = 'CLOSED'
            reason = f'Holiday - {holiday_name}'
            logger.warning(f"[MARKET STATUS] Market is CLOSED - {reason}")
            self._daily_market_status_cache = False
        else:
            status = 'OPEN'
            reason = 'Market is operational'
            logger.info(f"[MARKET STATUS] Market is OPEN - {reason}")
            self._daily_market_status_cache = True
        
        self._daily_market_status_date = today
        
        result = {
            'status': status,
            'is_open': status == 'OPEN',
            'reason': reason,
            'date': today.isoformat(),
            'check_time': now.strftime('%H:%M:%S'),
            'cached_for_day': True
        }
        
        logger.info(f"[CACHE] Market status cached until end of day {today}")
        return result
    
    def is_market_open(self) -> bool:
        """Check if market is currently open.
        
        Uses daily cache if available. If called at 9am, triggers full status check.
        
        Returns:
            True if market is open, False otherwise
        """
        try:
            now = datetime.now()
            today = now.date()
            
            if self._daily_market_status_cache is not None and self._daily_market_status_date == today:
                logger.debug(f"Using cached market status for {today}: {self._daily_market_status_cache}")
                return self._daily_market_status_cache
            
            if not self.kite:
                logger.warning("Kite client not provided, using time-based check only")
                return self._time_based_check()
            
            if not self._is_weekday(now):
                return False
            
            if self._is_holiday(now.date()):
                return False
            
            return self._is_within_market_hours(now)
        
        except Exception as e:
            logger.error(f"Error checking market status: {e}")
            return False
    
    def get_market_status(self) -> Dict:
        """Get detailed market status information.
        
        Uses daily cache for consistency if available. Updates cache at market open (9:00 AM).
        
        Returns:
            Dictionary with status, market_open boolean, and reason
            
            Example:
            {
                'status': 'OPEN',
                'market_open': True,
                'reason': 'Market is open',
                'current_time': '09:30:00',
                'market_open_time': '09:15',
                'market_close_time': '15:30',
                'cached': False
            }
        """
        try:
            now = datetime.now()
            today = now.date()
            
            if self._daily_market_status_cache is not None and self._daily_market_status_date == today:
                logger.debug(f"Using cached market status for {today}")
                cached_status = self._daily_market_status_cache
                
                if not cached_status:
                    return {
                        'status': 'CLOSED',
                        'market_open': False,
                        'reason': 'Market is closed (cached status)',
                        'current_time': now.strftime('%H:%M:%S'),
                        'cached': True,
                        'cache_date': today.isoformat()
                    }
                else:
                    return {
                        'status': 'OPEN',
                        'market_open': True,
                        'reason': 'Market is open (cached status)',
                        'current_time': now.strftime('%H:%M:%S'),
                        'market_open_time': self.MARKET_OPEN_TIME.strftime('%H:%M'),
                        'market_close_time': self.MARKET_CLOSE_TIME.strftime('%H:%M'),
                        'cached': True,
                        'cache_date': today.isoformat()
                    }
            
            if not self.kite:
                logger.warning("Kite client not provided, using time-based check only")
                return self._time_based_status()
            
            if not self._is_weekday(now):
                return {
                    'status': 'CLOSED',
                    'market_open': False,
                    'reason': 'Market closed on weekends',
                    'day_name': now.strftime('%A'),
                    'current_time': now.strftime('%H:%M:%S')
                }
            
            if self._is_holiday(now.date()):
                holiday_name = self._get_holiday_name(now.date())
                return {
                    'status': 'CLOSED',
                    'market_open': False,
                    'reason': f'Market closed on holiday',
                    'holiday_name': holiday_name,
                    'current_time': now.strftime('%H:%M:%S')
                }
            
            if not self._is_within_market_hours(now):
                if now.time() < self.MARKET_OPEN_TIME:
                    return {
                        'status': 'CLOSED',
                        'market_open': False,
                        'reason': f'Market not yet opened',
                        'market_open_time': self.MARKET_OPEN_TIME.strftime('%H:%M'),
                        'current_time': now.strftime('%H:%M:%S'),
                        'time_to_open_seconds': int((datetime.combine(now.date(), self.MARKET_OPEN_TIME) - now).total_seconds())
                    }
                else:
                    return {
                        'status': 'CLOSED',
                        'market_open': False,
                        'reason': f'Market already closed',
                        'market_close_time': self.MARKET_CLOSE_TIME.strftime('%H:%M'),
                        'current_time': now.strftime('%H:%M:%S')
                    }
            
            return {
                'status': 'OPEN',
                'market_open': True,
                'reason': 'Market is open',
                'current_time': now.strftime('%H:%M:%S'),
                'market_open_time': self.MARKET_OPEN_TIME.strftime('%H:%M'),
                'market_close_time': self.MARKET_CLOSE_TIME.strftime('%H:%M'),
                'time_to_close_seconds': int((datetime.combine(now.date(), self.MARKET_CLOSE_TIME) - now).total_seconds())
            }
        
        except Exception as e:
            logger.error(f"Error getting market status: {e}")
            return {
                'status': 'ERROR',
                'market_open': False,
                'reason': str(e)
            }
    
    def _check_market_holidays_support(self) -> bool:
        """Check if KiteConnect supports market_holidays method."""
        if not self.kite:
            return False
        
        return hasattr(self.kite, 'market_holidays') and callable(getattr(self.kite, 'market_holidays'))
    
    def _fetch_holidays_from_upstox(self) -> Optional[Dict[str, str]]:
        """Fetch market holidays from Upstox API."""
        try:
            logger.debug(f"Fetching market holidays from Upstox API: {UPSTOX_HOLIDAYS_API}")
            
            response = requests.get(UPSTOX_HOLIDAYS_API, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            holidays_dict = {}
            
            if data.get('status') == 'success' and data.get('data'):
                holidays_list = data.get('data', [])
                
                for holiday in holidays_list:
                    if isinstance(holiday, dict):
                        date_str = holiday.get('date')
                        description = holiday.get('description', 'Market Holiday')
                        if date_str:
                            holidays_dict[date_str] = description
                    elif isinstance(holiday, str):
                        holidays_dict[holiday] = 'Market Holiday'
                
                logger.info(f"Successfully fetched {len(holidays_dict)} holidays from Upstox API")
                self._api_holidays_cache = holidays_dict
                return holidays_dict
            else:
                logger.warning(f"Upstox API returned unexpected format: {data}")
                return None
        
        except requests.exceptions.Timeout:
            logger.warning("Timeout fetching holidays from Upstox API (10s)")
            return None
        except requests.exceptions.RequestException as e:
            logger.warning(f"Error fetching holidays from Upstox API: {e}")
            return None
        except Exception as e:
            logger.warning(f"Unexpected error fetching Upstox holidays: {e}")
            return None
    
    def _get_holidays_dict(self) -> Dict[str, str]:
        """Get holidays dictionary from Upstox API with caching."""
        if self._api_holidays_cache is not None:
            logger.debug("Using cached holidays from Upstox API")
            return self._api_holidays_cache
        
        upstox_holidays = self._fetch_holidays_from_upstox()
        
        if upstox_holidays:
            return upstox_holidays
        
        logger.warning("Could not fetch holidays from Upstox API, returning empty dict")
        return {}
    
    def get_holidays(self, year: Optional[int] = None) -> Dict[str, str]:
        """Get market holidays for a given year.
        
        Args:
            year: Year to get holidays for. If None, uses current year.
            
        Returns:
            Dictionary mapping date strings to holiday names
        """
        try:
            if not self.kite and not ALL_HOLIDAYS:
                logger.warning("Kite client not provided and no cached holidays")
                return {}
            
            all_holidays = self._get_holidays_dict()
            
            if year is None:
                year = datetime.now().year
            
            holidays_dict = {}
            for date_str, description in all_holidays.items():
                try:
                    holiday_date = datetime.strptime(date_str, '%Y-%m-%d')
                    if holiday_date.year == year:
                        holidays_dict[date_str] = description
                except ValueError:
                    continue
            
            return holidays_dict
        
        except Exception as e:
            logger.error(f"Error getting market holidays: {e}")
            return {}
    
    def _is_weekday(self, dt: datetime) -> bool:
        """Check if date is a weekday (Monday-Friday)."""
        return dt.weekday() < 5
    
    def _is_within_market_hours(self, dt: datetime) -> bool:
        """Check if time is within market hours."""
        return self.MARKET_OPEN_TIME <= dt.time() <= self.MARKET_CLOSE_TIME
    
    def _is_holiday(self, date) -> bool:
        """Check if date is a market holiday."""
        try:
            target_date_str = date.strftime('%Y-%m-%d')
            holidays = self._get_holidays_dict()
            
            return target_date_str in holidays
        
        except Exception as e:
            logger.warning(f"Error checking holiday status: {e}")
            return False
    
    def _get_holiday_name(self, date) -> str:
        """Get the name of a holiday."""
        try:
            target_date_str = date.strftime('%Y-%m-%d')
            holidays = self._get_holidays_dict()
            
            return holidays.get(target_date_str, 'Unknown')
        
        except Exception as e:
            logger.warning(f"Error getting holiday name: {e}")
            return 'Unknown'
    
    def _time_based_check(self) -> bool:
        """Fallback time-based market check without API."""
        now = datetime.now()
        return self._is_weekday(now) and self._is_within_market_hours(now)
    
    def _time_based_status(self) -> Dict:
        """Fallback time-based status without API."""
        now = datetime.now()
        
        if not self._is_weekday(now):
            return {
                'status': 'CLOSED',
                'market_open': False,
                'reason': 'Market closed on weekends',
                'day_name': now.strftime('%A'),
                'current_time': now.strftime('%H:%M:%S')
            }
        
        if not self._is_within_market_hours(now):
            if now.time() < self.MARKET_OPEN_TIME:
                return {
                    'status': 'CLOSED',
                    'market_open': False,
                    'reason': 'Market not yet opened',
                    'market_open_time': self.MARKET_OPEN_TIME.strftime('%H:%M'),
                    'current_time': now.strftime('%H:%M:%S')
                }
            else:
                return {
                    'status': 'CLOSED',
                    'market_open': False,
                    'reason': 'Market already closed',
                    'market_close_time': self.MARKET_CLOSE_TIME.strftime('%H:%M'),
                    'current_time': now.strftime('%H:%M:%S')
                }
        
        return {
            'status': 'OPEN',
            'market_open': True,
            'reason': 'Market is open (time-based check)',
            'current_time': now.strftime('%H:%M:%S'),
            'market_open_time': self.MARKET_OPEN_TIME.strftime('%H:%M'),
            'market_close_time': self.MARKET_CLOSE_TIME.strftime('%H:%M')
        }
