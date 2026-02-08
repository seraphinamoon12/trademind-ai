"""Earnings filter - avoid trading around earnings announcements."""
from datetime import datetime, timedelta
from typing import Optional
import logging

import yfinance as yf

logger = logging.getLogger(__name__)


class EarningsFilter:
    """
    Avoid trading around earnings announcements.
    
    Filters:
    - Avoid 1 day before earnings
    - Avoid 1 day after earnings
    """
    
    AVOID_DAYS_BEFORE = 1
    AVOID_DAYS_AFTER = 1
    
    def __init__(self):
        self.earnings_cache: dict = {}  # symbol: (earnings_date, cached_at)
        self.cache_duration = timedelta(hours=6)  # Cache for 6 hours
    
    def is_safe_to_trade(self, symbol: str) -> bool:
        """
        Check if symbol has earnings soon (should avoid trading).
        
        Args:
            symbol: Stock symbol
            
        Returns:
            bool: True if safe to trade (no earnings soon)
        """
        days_to_earnings = self.get_days_to_earnings(symbol)
        
        if days_to_earnings is None:
            # If we can't get earnings data, allow trade
            return True
        
        # Check if within avoidance window
        if -self.AVOID_DAYS_AFTER <= days_to_earnings <= self.AVOID_DAYS_BEFORE:
            logger.warning(
                f"{symbol}: Earnings in {days_to_earnings} days, skipping"
            )
            return False
        
        return True
    
    def get_days_to_earnings(self, symbol: str) -> Optional[int]:
        """
        Get days until next earnings.
        
        Returns:
            int: Days to earnings (negative if past), or None if unknown
        """
        # Check cache
        if symbol in self.earnings_cache:
            earnings_date, cached_at = self.earnings_cache[symbol]
            if datetime.now() - cached_at < self.cache_duration:
                days = (earnings_date - datetime.now()).days
                return days
        
        try:
            ticker = yf.Ticker(symbol)
            calendar = ticker.calendar
            
            if calendar is None or calendar.empty:
                return None
            
            # Get next earnings date
            next_earnings = None
            
            # Try different ways to get earnings date
            if hasattr(calendar, 'index') and len(calendar.index) > 0:
                next_earnings = calendar.index[0]
            elif 'Earnings Date' in calendar.columns:
                next_earnings = calendar['Earnings Date'].iloc[0]
            
            if next_earnings is None:
                return None
            
            # Convert to datetime if needed
            if isinstance(next_earnings, str):
                next_earnings = datetime.strptime(next_earnings, '%Y-%m-%d')
            
            # Make timezone-naive for comparison
            if hasattr(next_earnings, 'tz_localize'):
                next_earnings = next_earnings.tz_localize(None)
            elif hasattr(next_earnings, 'to_pydatetime'):
                next_earnings = next_earnings.to_pydatetime()
            
            # Cache the result
            self.earnings_cache[symbol] = (next_earnings, datetime.now())
            
            # Calculate days
            days = (next_earnings - datetime.now()).days
            return days
            
        except Exception as e:
            logger.debug(f"Could not get earnings for {symbol}: {e}")
            return None
    
    def get_earnings_info(self, symbol: str) -> dict:
        """Get detailed earnings information."""
        days = self.get_days_to_earnings(symbol)
        
        if days is None:
            return {
                'symbol': symbol,
                'has_earnings_data': False,
                'safe_to_trade': True
            }
        
        is_safe = not (-self.AVOID_DAYS_AFTER <= days <= self.AVOID_DAYS_BEFORE)
        
        return {
            'symbol': symbol,
            'has_earnings_data': True,
            'days_to_earnings': days,
            'safe_to_trade': is_safe,
            'avoid_window': {
                'days_before': self.AVOID_DAYS_BEFORE,
                'days_after': self.AVOID_DAYS_AFTER
            },
            'recommendation': 'AVOID' if not is_safe else 'OK'
        }


# Global earnings filter instance
earnings_filter = EarningsFilter()
