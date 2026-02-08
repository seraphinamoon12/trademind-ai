"""Moving Average Crossover Strategy."""
import pandas as pd
from typing import Optional

from src.strategies.base import BaseStrategy, Signal, SignalType
from src.data.indicators import TechnicalIndicators
from src.config import settings


class MACrossoverStrategy(BaseStrategy):
    """
    Moving Average Crossover Strategy.
    
    Golden Cross: Fast MA crosses above Slow MA = BUY
    Death Cross: Fast MA crosses below Slow MA = SELL
    """
    
    name = "ma_crossover"
    description = "MA Crossover - Golden Cross buy, Death Cross sell"
    
    def __init__(
        self,
        fast_period: int = None,
        slow_period: int = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.fast_period = fast_period or settings.ma_fast
        self.slow_period = slow_period or settings.ma_slow
    
    def generate_signal(self, df: pd.DataFrame, symbol: str) -> Optional[Signal]:
        """Generate signal based on MA crossover."""
        if not self.validate_data(df):
            return None
        
        # Need enough data
        if len(df) < self.slow_period + 5:
            return None
        
        # Add indicators
        df = TechnicalIndicators.add_all_indicators(df)
        
        # Get current and previous values for crossover detection
        if len(df) < 2:
            return None
        
        current = df.iloc[-1]
        previous = df.iloc[-2]
        
        # Use appropriate MA columns based on periods
        fast_col = f'sma_{self.fast_period}' if self.fast_period in [20, 50] else 'sma_50'
        slow_col = f'sma_{self.slow_period}' if self.slow_period == 200 else 'sma_200'
        
        current_fast = current.get(fast_col)
        current_slow = current.get(slow_col)
        prev_fast = previous.get(fast_col)
        prev_slow = previous.get(slow_col)
        
        if pd.isna(current_fast) or pd.isna(current_slow):
            return None
        
        price = float(current['close'])
        signal_type = SignalType.HOLD
        confidence = 0.5
        
        # Detect crossover
        if prev_fast is not None and prev_slow is not None and not pd.isna(prev_fast) and not pd.isna(prev_slow):
            # Golden Cross: fast crosses above slow
            if prev_fast <= prev_slow and current_fast > current_slow:
                signal_type = SignalType.BUY
                confidence = 0.8
            # Death Cross: fast crosses below slow
            elif prev_fast >= prev_slow and current_fast < current_slow:
                signal_type = SignalType.SELL
                confidence = 0.8
        
        # Trend following (weaker signal if no crossover)
        if signal_type == SignalType.HOLD:
            if current_fast > current_slow * 1.02:  # Fast well above slow
                signal_type = SignalType.BUY
                confidence = 0.6
            elif current_fast < current_slow * 0.98:  # Fast well below slow
                signal_type = SignalType.SELL
                confidence = 0.6
            else:
                return None  # No clear signal
        
        return Signal(
            symbol=symbol,
            signal=signal_type,
            confidence=round(confidence, 2),
            strategy=self.name,
            price=price,
            timestamp=pd.Timestamp.now(),
            metadata={
                'fast_ma': round(current_fast, 2),
                'slow_ma': round(current_slow, 2),
                'fast_period': self.fast_period,
                'slow_period': self.slow_period,
                'crossover_detected': confidence >= 0.7
            }
        )
