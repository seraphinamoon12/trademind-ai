"""Data validation layer - detect stale or suspicious data."""
from datetime import datetime, timedelta
from typing import Tuple, Optional
import logging

import pandas as pd

logger = logging.getLogger(__name__)


class DataValidator:
    """
    Validate market data before using.
    
    Checks:
    - Data staleness (max 15 minutes old)
    - Suspicious price moves (max 20% change)
    - Zero/null prices
    """
    
    MAX_DATA_AGE_MINUTES = 15
    MAX_PRICE_CHANGE_PCT = 0.20  # 20%
    
    def __init__(self):
        self.price_history: dict = {}  # symbol: [(price, timestamp), ...]
        self.max_history = 10
    
    def validate_price_data(
        self, 
        symbol: str, 
        current_price: float, 
        timestamp: datetime = None,
        previous_price: float = None
    ) -> Tuple[bool, str]:
        """
        Check if price data is valid.
        
        Args:
            symbol: Stock symbol
            current_price: Current price
            timestamp: Data timestamp (defaults to now)
            previous_price: Previous price for change calculation
            
        Returns:
            Tuple[bool, str]: (is_valid, reason)
        """
        # Default timestamp
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        # Check for zero/null prices
        if current_price is None or current_price <= 0 or pd.isna(current_price):
            return False, "Invalid price (zero/null/NaN)"
        
        # Check staleness
        age = (datetime.utcnow() - timestamp).total_seconds() / 60
        if age > self.MAX_DATA_AGE_MINUTES:
            return False, f"Data stale: {age:.1f} min old"
        
        # Get previous price if not provided
        if previous_price is None and symbol in self.price_history:
            if len(self.price_history[symbol]) > 0:
                previous_price = self.price_history[symbol][-1][0]
        
        # Check for suspicious price moves
        if previous_price and previous_price > 0:
            change_pct = abs(current_price - previous_price) / previous_price
            if change_pct > self.MAX_PRICE_CHANGE_PCT:
                return False, f"Suspicious move: {change_pct:.1%}"
        
        # Store price in history
        if symbol not in self.price_history:
            self.price_history[symbol] = []
        self.price_history[symbol].append((current_price, timestamp))
        if len(self.price_history[symbol]) > self.max_history:
            self.price_history[symbol] = self.price_history[symbol][-self.max_history:]
        
        return True, "OK"
    
    def validate_ohlcv_data(
        self,
        symbol: str,
        data: pd.DataFrame
    ) -> Tuple[bool, str]:
        """
        Validate OHLCV data.
        
        Args:
            symbol: Stock symbol
            data: DataFrame with open, high, low, close, volume
            
        Returns:
            Tuple[bool, str]: (is_valid, reason)
        """
        if data is None or data.empty:
            return False, "Empty data"
        
        if len(data) < 2:
            return False, "Insufficient data"
        
        # Check required columns
        required = ['open', 'high', 'low', 'close', 'volume']
        for col in required:
            if col not in data.columns:
                return False, f"Missing column: {col}"
        
        # Check for zero/null prices
        last = data.iloc[-1]
        for col in ['open', 'high', 'low', 'close']:
            if last[col] <= 0 or pd.isna(last[col]):
                return False, f"Invalid {col} price: {last[col]}"
        
        # Check OHLC logic
        if last['low'] > last['high']:
            return False, "Low > High"
        if last['close'] > last['high'] or last['close'] < last['low']:
            return False, "Close outside High-Low range"
        if last['open'] > last['high'] or last['open'] < last['low']:
            return False, "Open outside High-Low range"
        
        # Check for suspicious price jump
        if len(data) >= 2:
            prev_close = data.iloc[-2]['close']
            curr_close = last['close']
            change_pct = abs(curr_close - prev_close) / prev_close
            if change_pct > self.MAX_PRICE_CHANGE_PCT:
                return False, f"Suspicious price jump: {change_pct:.1%}"
        
        return True, "OK"
    
    def get_data_quality(self, symbol: str) -> dict:
        """Get data quality metrics for a symbol."""
        history = self.price_history.get(symbol, [])
        
        if not history:
            return {
                'symbol': symbol,
                'has_history': False,
                'last_price': None,
                'last_timestamp': None
            }
        
        last_price, last_ts = history[-1]
        age = (datetime.utcnow() - last_ts).total_seconds() / 60
        
        return {
            'symbol': symbol,
            'has_history': True,
            'last_price': last_price,
            'last_timestamp': last_ts.isoformat(),
            'age_minutes': age,
            'is_fresh': age <= self.MAX_DATA_AGE_MINUTES,
            'history_count': len(history)
        }


# Global data validator instance
data_validator = DataValidator()
