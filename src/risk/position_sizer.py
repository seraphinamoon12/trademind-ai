"""Volatility-based position sizing using ATR."""
from typing import Optional, Dict, Any
import logging

import yfinance as yf
import pandas as pd

logger = logging.getLogger(__name__)


class VolatilityPositionSizer:
    """
    Size positions based on volatility (ATR) rather than fixed percentage.
    
    Goal: Equal risk per position, not equal capital per position.
    
    Formula: Position Size = Risk Amount / (ATR × multiplier)
    Example: $1,000 risk / ($2 ATR × 2) = 250 shares
    """
    
    RISK_PER_TRADE_PCT = 0.02  # 2% of portfolio per trade
    MAX_POSITION_PCT = 0.10    # 10% max (hard ceiling)
    ATR_PERIOD = 14
    ATR_MULTIPLIER = 2.0       # 2× ATR for stop distance
    
    def __init__(self):
        self.atr_cache: Dict[str, tuple] = {}  # symbol: (atr, timestamp)
    
    def calculate_position_size(
        self,
        portfolio_value: float,
        symbol: str,
        entry_price: float,
        atr: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Calculate position size based on volatility (ATR).
        
        Args:
            portfolio_value: Total portfolio value
            symbol: Stock symbol
            entry_price: Entry price per share
            atr: Optional pre-calculated ATR
            
        Returns:
            dict: Position sizing details with keys:
                - shares: Number of shares to buy
                - position_value: Dollar value of position
                - position_pct: % of portfolio
                - stop_price: Stop loss price level
                - risk_amount: Dollar amount at risk
                - risk_pct: % of portfolio at risk
                - atr: ATR value used
                - method: 'volatility' or 'fallback_fixed'
        """
        if entry_price is None or entry_price <= 0:
            logger.error(f"Invalid entry price for {symbol}: {entry_price}")
            return self._fallback_sizing(portfolio_value, entry_price)
        
        # Get ATR if not provided
        if atr is None:
            atr = self.get_atr(symbol)
        
        if atr is None or atr <= 0:
            logger.warning(f"Could not calculate ATR for {symbol}, using fixed sizing")
            return self._fallback_sizing(portfolio_value, entry_price)
        
        # Calculate stop distance in dollars (2× ATR)
        stop_distance = atr * self.ATR_MULTIPLIER
        
        # Calculate risk amount (2% of portfolio)
        risk_amount = portfolio_value * self.RISK_PER_TRADE_PCT
        
        # Calculate position size: Risk Amount / Stop Distance
        if stop_distance > 0:
            shares = int(risk_amount / stop_distance)
        else:
            shares = 0
        
        # Calculate position value
        position_value = shares * entry_price
        position_pct = position_value / portfolio_value if portfolio_value > 0 else 0
        
        # Enforce max position size (10% ceiling)
        max_position_value = portfolio_value * self.MAX_POSITION_PCT
        if position_value > max_position_value:
            shares = int(max_position_value / entry_price)
            position_value = shares * entry_price
            position_pct = position_value / portfolio_value if portfolio_value > 0 else 0
            risk_amount = shares * stop_distance
            logger.info(f"Position capped at {self.MAX_POSITION_PCT:.0%} max: {shares} shares")
        
        # Calculate stop price
        stop_price = entry_price - stop_distance
        
        return {
            'shares': shares,
            'position_value': position_value,
            'position_pct': position_pct,
            'stop_price': stop_price,
            'stop_distance': stop_distance,
            'stop_distance_pct': stop_distance / entry_price if entry_price > 0 else 0,
            'risk_amount': shares * stop_distance,
            'risk_pct': (shares * stop_distance) / portfolio_value if portfolio_value > 0 else 0,
            'atr': atr,
            'method': 'volatility'
        }
    
    def _fallback_sizing(
        self, 
        portfolio_value: float, 
        entry_price: float
    ) -> Dict[str, Any]:
        """Fallback to fixed 10% sizing if ATR unavailable."""
        if entry_price is None or entry_price <= 0:
            return {
                'shares': 0,
                'position_value': 0,
                'position_pct': 0,
                'stop_price': 0,
                'stop_distance': 0,
                'stop_distance_pct': 0,
                'risk_amount': 0,
                'risk_pct': 0,
                'atr': None,
                'method': 'fallback_fixed',
                'error': 'Invalid price'
            }
        
        position_value = portfolio_value * 0.10
        shares = int(position_value / entry_price)
        
        stop_distance = entry_price * 0.05  # Fixed 5% stop
        
        return {
            'shares': shares,
            'position_value': shares * entry_price,
            'position_pct': (shares * entry_price) / portfolio_value if portfolio_value > 0 else 0,
            'stop_price': entry_price * 0.95,
            'stop_distance': stop_distance,
            'stop_distance_pct': 0.05,
            'risk_amount': shares * stop_distance,
            'risk_pct': (shares * stop_distance) / portfolio_value if portfolio_value > 0 else 0,
            'atr': None,
            'method': 'fallback_fixed'
        }
    
    def get_atr(self, symbol: str, period: int = None) -> Optional[float]:
        """
        Calculate Average True Range for volatility measurement.
        
        Args:
            symbol: Stock symbol
            period: ATR period (defaults to self.ATR_PERIOD)
            
        Returns:
            float: ATR value or None if calculation fails
        """
        if period is None:
            period = self.ATR_PERIOD
        
        try:
            hist = yf.Ticker(symbol).history(period=f"{period + 10}d")
            
            if len(hist) < period:
                logger.warning(f"Insufficient data for {symbol} ATR calculation")
                return None
            
            # Calculate True Range
            high = hist['High']
            low = hist['Low']
            close = hist['Close']
            
            tr1 = high - low
            tr2 = abs(high - close.shift())
            tr3 = abs(low - close.shift())
            
            true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = true_range.rolling(window=period).mean().iloc[-1]
            
            return float(atr) if pd.notna(atr) else None
            
        except Exception as e:
            logger.warning(f"Error calculating ATR for {symbol}: {e}")
            return None
    
    def calculate_atr_from_data(
        self, 
        data: pd.DataFrame, 
        period: int = None
    ) -> Optional[float]:
        """
        Calculate ATR from provided OHLCV data.
        
        Args:
            data: DataFrame with 'high', 'low', 'close' columns
            period: ATR period
            
        Returns:
            float: ATR value or None
        """
        if period is None:
            period = self.ATR_PERIOD
        
        if data is None or len(data) < period:
            return None
        
        try:
            high = data['high']
            low = data['low']
            close = data['close']
            
            tr1 = high - low
            tr2 = abs(high - close.shift())
            tr3 = abs(low - close.shift())
            
            true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = true_range.rolling(window=period).mean().iloc[-1]
            
            return float(atr) if pd.notna(atr) else None
            
        except Exception as e:
            logger.warning(f"Error calculating ATR from data: {e}")
            return None


# Global position sizer instance
position_sizer = VolatilityPositionSizer()
