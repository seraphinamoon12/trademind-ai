"""Base strategy class."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List
from enum import Enum
import pandas as pd


class SignalType(Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass
class Signal:
    """Trading signal from a strategy."""
    symbol: str
    signal: SignalType
    confidence: float  # 0.0 to 1.0
    strategy: str
    price: float
    timestamp: pd.Timestamp
    metadata: dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class BaseStrategy(ABC):
    """Base class for all trading strategies."""
    
    name: str = "base"
    description: str = "Base strategy"
    
    def __init__(self, **kwargs):
        self.params = kwargs
    
    @abstractmethod
    def generate_signal(self, df: pd.DataFrame, symbol: str) -> Optional[Signal]:
        """Generate trading signal from price data."""
        pass
    
    def validate_data(self, df: pd.DataFrame) -> bool:
        """Validate that dataframe has required data."""
        if df is None or df.empty:
            return False
        required = ['open', 'high', 'low', 'close', 'volume']
        return all(col in df.columns for col in required)
    
    def get_latest_price(self, df: pd.DataFrame) -> float:
        """Get latest closing price."""
        return float(df['close'].iloc[-1])
