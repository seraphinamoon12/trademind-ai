"""Technical Analysis Agent."""
import pandas as pd
from typing import Optional

from src.agents.base import BaseAgent, AgentSignal, AgentDecision
from src.data.indicators import TechnicalIndicators
from src.strategies.rsi_reversion import RSIMeanReversionStrategy
from src.strategies.ma_crossover import MACrossoverStrategy
from src.config import settings


class TechnicalAgent(BaseAgent):
    """
    Technical Analysis Agent.
    
    Uses rule-based strategies (RSI, MA Crossover) to generate signals.
    No LLM - pure technical analysis.
    """
    
    name = "technical"
    weight = settings.technical_weight
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.rsi_strategy = RSIMeanReversionStrategy()
        self.ma_strategy = MACrossoverStrategy()
    
    async def analyze(self, symbol: str, data: pd.DataFrame, **context) -> AgentSignal:
        """Analyze technical indicators and return signal."""
        if data is None or data.empty:
            return AgentSignal(
                agent_name=self.name,
                symbol=symbol,
                decision=AgentDecision.HOLD,
                confidence=0.0,
                reasoning="No data available"
            )
        
        # Generate signals from both strategies
        signals = []
        
        if settings.rsi_enabled:
            rsi_signal = self.rsi_strategy.generate_signal(data, symbol)
            if rsi_signal:
                signals.append(rsi_signal)
        
        if settings.ma_enabled:
            ma_signal = self.ma_strategy.generate_signal(data, symbol)
            if ma_signal:
                signals.append(ma_signal)
        
        if not signals:
            return AgentSignal(
                agent_name=self.name,
                symbol=symbol,
                decision=AgentDecision.HOLD,
                confidence=0.5,
                reasoning="No clear technical signals"
            )
        
        # Combine signals - take the one with highest confidence
        best_signal = max(signals, key=lambda s: s.confidence)
        
        # Map SignalType to AgentDecision
        decision_map = {
            "BUY": AgentDecision.BUY,
            "SELL": AgentDecision.SELL,
            "HOLD": AgentDecision.HOLD
        }
        
        # Build reasoning
        reasoning_parts = []
        for sig in signals:
            reasoning_parts.append(
                f"{sig.strategy}: {sig.signal.value} "
                f"(confidence: {sig.confidence})"
            )
        
        return AgentSignal(
            agent_name=self.name,
            symbol=symbol,
            decision=decision_map.get(best_signal.signal.value, AgentDecision.HOLD),
            confidence=best_signal.confidence,
            reasoning=f"Selected {best_signal.strategy}. " + "; ".join(reasoning_parts),
            data={
                'selected_strategy': best_signal.strategy,
                'all_signals': [
                    {
                        'strategy': s.strategy,
                        'signal': s.signal.value,
                        'confidence': s.confidence,
                        'metadata': s.metadata
                    }
                    for s in signals
                ]
            }
        )
