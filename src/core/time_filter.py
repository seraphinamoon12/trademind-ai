"""Time-based trading restrictions."""
from datetime import time, datetime, date
from typing import Tuple
from zoneinfo import ZoneInfo
import logging

logger = logging.getLogger(__name__)


class TimeFilter:
    """
    Time-based trading restrictions.
    
    - Market hours only (9:30 AM - 4:00 PM ET)
    - No new trades after 3:30 PM ET
    - Holiday checking
    """
    
    # Market hours (Eastern Time)
    MARKET_OPEN = time(9, 30, tzinfo=ZoneInfo("America/New_York"))
    MARKET_CLOSE = time(16, 0, tzinfo=ZoneInfo("America/New_York"))
    NO_NEW_TRADES_AFTER = time(15, 30, tzinfo=ZoneInfo("America/New_York"))
    
    # US Market holidays 2024-2025 (simplified - should be updated annually)
    MARKET_HOLIDAYS = {
        date(2024, 1, 1),   # New Year's Day
        date(2024, 1, 15),  # MLK Day
        date(2024, 2, 19),  # Presidents Day
        date(2024, 3, 29),  # Good Friday
        date(2024, 5, 27),  # Memorial Day
        date(2024, 6, 19),  # Juneteenth
        date(2024, 7, 4),   # Independence Day
        date(2024, 9, 2),   # Labor Day
        date(2024, 11, 28), # Thanksgiving
        date(2024, 12, 25), # Christmas
        date(2025, 1, 1),   # New Year's Day
        date(2025, 1, 20),  # MLK Day
        date(2025, 2, 17),  # Presidents Day
        date(2025, 4, 18),  # Good Friday
        date(2025, 5, 26),  # Memorial Day
        date(2025, 6, 19),  # Juneteenth
        date(2025, 7, 4),   # Independence Day
        date(2025, 9, 1),   # Labor Day
        date(2025, 11, 27), # Thanksgiving
        date(2025, 12, 25), # Christmas
    }
    
    def is_market_open(self, check_time: datetime = None) -> bool:
        """
        Check if market is currently open.
        
        Args:
            check_time: Time to check (defaults to now)
            
        Returns:
            bool: True if market is open
        """
        if check_time is None:
            check_time = datetime.now(ZoneInfo("America/New_York"))
        else:
            # Ensure timezone aware
            if check_time.tzinfo is None:
                check_time = check_time.replace(tzinfo=ZoneInfo("America/New_York"))
        
        # Check weekday (0=Monday, 5=Saturday, 6=Sunday)
        if check_time.weekday() >= 5:
            return False
        
        # Check holiday
        if check_time.date() in self.MARKET_HOLIDAYS:
            return False
        
        # Check market hours
        current_time = check_time.time()
        return self.MARKET_OPEN <= current_time <= self.MARKET_CLOSE
    
    def can_open_new_position(self, check_time: datetime = None) -> Tuple[bool, str]:
        """
        Check if new positions can be opened.
        
        Returns:
            Tuple[bool, str]: (can_trade, reason)
        """
        if check_time is None:
            check_time = datetime.now(ZoneInfo("America/New_York"))
        else:
            if check_time.tzinfo is None:
                check_time = check_time.replace(tzinfo=ZoneInfo("America/New_York"))
        
        # Check market is open
        if not self.is_market_open(check_time):
            return False, "Market is closed"
        
        # Check cutoff time for new trades
        current_time = check_time.time()
        if current_time > self.NO_NEW_TRADES_AFTER:
            return False, f"No new trades after {self.NO_NEW_TRADES_AFTER.strftime('%H:%M')} ET"
        
        return True, "OK"
    
    def can_close_position(self, check_time: datetime = None) -> Tuple[bool, str]:
        """
        Check if positions can be closed.
        
        Closing is allowed any time market is open.
        """
        if check_time is None:
            check_time = datetime.now(ZoneInfo("America/New_York"))
        else:
            if check_time.tzinfo is None:
                check_time = check_time.replace(tzinfo=ZoneInfo("America/New_York"))
        
        if not self.is_market_open(check_time):
            return False, "Market is closed"
        
        return True, "OK"
    
    def get_market_status(self) -> dict:
        """Get current market status."""
        now = datetime.now(ZoneInfo("America/New_York"))
        
        is_open = self.is_market_open(now)
        can_open_new, new_reason = self.can_open_new_position(now)
        can_close, close_reason = self.can_close_position(now)
        
        return {
            'is_market_open': is_open,
            'current_time': now.isoformat(),
            'market_open_time': self.MARKET_OPEN.strftime('%H:%M'),
            'market_close_time': self.MARKET_CLOSE.strftime('%H:%M'),
            'no_new_trades_after': self.NO_NEW_TRADES_AFTER.strftime('%H:%M'),
            'can_open_new_position': can_open_new,
            'can_close_position': can_close,
            'new_position_reason': new_reason,
            'close_position_reason': close_reason,
            'is_weekend': now.weekday() >= 5,
            'is_holiday': now.date() in self.MARKET_HOLIDAYS
        }
    
    def time_until_market_open(self) -> float:
        """
        Get minutes until market opens.
        
        Returns:
            float: Minutes until open (0 if open now)
        """
        now = datetime.now(ZoneInfo("America/New_York"))
        
        if self.is_market_open(now):
            return 0.0
        
        # Find next market open
        days_ahead = 0
        check_date = now.date()
        
        while days_ahead < 7:
            check_date = now.date() + __import__('datetime').timedelta(days=days_ahead)
            
            # Skip weekends
            if check_date.weekday() >= 5:
                days_ahead += 1
                continue
            
            # Skip holidays
            if check_date in self.MARKET_HOLIDAYS:
                days_ahead += 1
                continue
            
            # This is a valid trading day
            break
            
            days_ahead += 1
        
        next_open = datetime.combine(check_date, self.MARKET_OPEN.replace(tzinfo=None))
        next_open = next_open.replace(tzinfo=ZoneInfo("America/New_York"))
        
        delta = next_open - now
        return delta.total_seconds() / 60.0


# Global time filter instance
time_filter = TimeFilter()
