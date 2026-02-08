"""Base agent class."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any
from enum import Enum
import pandas as pd


class AgentDecision(Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    VETO = "VETO"


@dataclass
class AgentSignal:
    """Signal from an agent."""
    agent_name: str
    symbol: str
    decision: AgentDecision
    confidence: float  # 0.0 to 1.0
    reasoning: str
    data: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.data is None:
            self.data = {}


class BaseAgent(ABC):
    """Base class for all trading agents."""
    
    name: str = "base"
    weight: float = 1.0
    can_veto: bool = False
    
    def __init__(self, **kwargs):
        self.config = kwargs
    
    @abstractmethod
    async def analyze(self, symbol: str, data: pd.DataFrame, **context) -> AgentSignal:
        """Analyze data and return a signal."""
        pass
    
    def log_decision(self, signal: AgentSignal) -> None:
        """Log agent decision to database."""
        # This will be implemented to log to AgentDecision table
        pass
