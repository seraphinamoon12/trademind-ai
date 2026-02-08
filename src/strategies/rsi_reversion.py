"""RSI Mean Reversion Strategy."""
import pandas as pd
from typing import Optional

from src.strategies.base import BaseStrategy, Signal, SignalType
from src.data.indicators import TechnicalIndicators
from src.config import settings


class RSIMeanReversionStrategy(BaseStrategy):
    """
    RSI Mean Reversion Strategy.
    
    Buys when RSI is oversold (below threshold)
    Sells when RSI is overbought (above threshold)
    """
    
    name = "rsi_mean_reversion"
    description = "RSI Mean Reversion - Buy oversold, Sell overbought"
    
    def __init__(
        self,
        rsi_period: int = None,
        oversold: float = None,
        overbought: float = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.rsi_period = rsi_period or settings.rsi_period
        self.oversold = oversold or settings.rsi_oversold
        self.overbought = overbought or settings.rsi_overbought
    
    def generate_signal(self, df: pd.DataFrame, symbol: str) -> Optional[Signal]:
        """Generate signal based on RSI."""
        if not self.validate_data(df):
            return None
        
        # Need enough data for RSI calculation
        if len(df) < self.rsi_period + 10:
            return None
        
        # Add indicators
        df = TechnicalIndicators.add_all_indicators(df)
        
        # Get latest values
        latest = df.iloc[-1]
        rsi = latest.get('rsi')
        price = float(latest['close'])
        
        if pd.isna(rsi):
            return None
        
        # Generate signal
        signal_type = SignalType.HOLD
        confidence = 0.5
        
        if rsi <= self.oversold:
            signal_type = SignalType.BUY
            # Higher confidence the more oversold
            confidence = min(0.9, 0.5 + (self.oversold - rsi) / 50)
        elif rsi >= self.overbought:
            signal_type = SignalType.SELL
            # Higher confidence the more overbought
            confidence = min(0.9, 0.5 + (rsi - self.overbought) / 50)
        
        if signal_type == SignalType.HOLD:
            return None
        
        return Signal(
            symbol=symbol,
            signal=signal_type,
            confidence=round(confidence, 2),
            strategy=self.name,
            price=price,
            timestamp=pd.Timestamp.now(),
            metadata={
                'rsi': round(rsi, 2),
                'oversold_threshold': self.oversold,
                'overbought_threshold': self.overbought,
                'rsi_period': self.rsi_period
            }
        )
