"""Orchestrator - Combines agent signals."""
from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum

from src.agents.base import BaseAgent, AgentSignal, AgentDecision
from src.config import settings
from src.core.safety_manager import safety_manager


class FinalDecision(Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass
class TradeDecision:
    """Final trade decision from orchestrator."""
    symbol: str
    decision: FinalDecision
    confidence: float
    quantity: int
    reasoning: str
    agent_signals: List[AgentSignal]
    safety_blocked: bool = False
    safety_reason: str = None
    
    def to_dict(self) -> dict:
        return {
            'symbol': self.symbol,
            'decision': self.decision.value,
            'confidence': self.confidence,
            'quantity': self.quantity,
            'reasoning': self.reasoning,
            'safety_blocked': self.safety_blocked,
            'safety_reason': self.safety_reason,
            'agent_signals': [
                {
                    'agent': s.agent_name,
                    'decision': s.decision.value,
                    'confidence': s.confidence,
                    'reasoning': s.reasoning
                }
                for s in self.agent_signals
            ]
        }


class Orchestrator:
    """
    Orchestrator combines signals from all agents.
    
    Uses weighted voting where:
    - Technical: 40%
    - Sentiment: 30% (if enabled)
    - Risk: 30% (can veto)
    
    Now integrated with Safety Manager for:
    - Circuit breaker checks
    - Position limit checks
    - Time restrictions
    - Volatility-based position sizing
    """
    
    def __init__(self):
        self.min_confidence = 0.6
        self.weights = {
            'technical': settings.technical_weight,
            'sentiment': settings.sentiment_weight if settings.sentiment_enabled else 0,
            'risk': settings.risk_weight
        }
    
    def decide(
        self,
        symbol: str,
        signals: List[AgentSignal],
        portfolio_value: float = 100000,
        current_price: float = 0,
        holdings: Dict = None,
        daily_pnl: float = 0,
        daily_pnl_pct: float = 0
    ) -> TradeDecision:
        """Combine agent signals into final decision with safety checks."""
        
        holdings = holdings or {}
        
        # ===== SAFETY CHECKS FIRST =====
        can_trade, safety_reason = safety_manager.check_can_trade(
            portfolio_value=portfolio_value,
            daily_pnl=daily_pnl,
            daily_pnl_pct=daily_pnl_pct
        )
        
        if not can_trade:
            return TradeDecision(
                symbol=symbol,
                decision=FinalDecision.HOLD,
                confidence=0.0,
                quantity=0,
                reasoning=f"SAFETY BLOCK: {safety_reason}",
                agent_signals=signals,
                safety_blocked=True,
                safety_reason=safety_reason
            )
        
        if not signals:
            return TradeDecision(
                symbol=symbol,
                decision=FinalDecision.HOLD,
                confidence=0.0,
                quantity=0,
                reasoning="No signals received",
                agent_signals=[]
            )
        
        # Check for veto (risk agent can veto)
        for signal in signals:
            if signal.decision == AgentDecision.VETO:
                return TradeDecision(
                    symbol=symbol,
                    decision=FinalDecision.HOLD,
                    confidence=1.0,
                    quantity=0,
                    reasoning=f"TRADE VETOED by {signal.agent_name}: {signal.reasoning}",
                    agent_signals=signals
                )
        
        # Calculate weighted scores
        buy_score = 0.0
        sell_score = 0.0
        total_weight = 0.0
        
        for signal in signals:
            weight = self.weights.get(signal.agent_name, 0.33)
            
            if signal.decision == AgentDecision.BUY:
                buy_score += signal.confidence * weight
            elif signal.decision == AgentDecision.SELL:
                sell_score += signal.confidence * weight
            
            total_weight += weight
        
        # Normalize scores
        if total_weight > 0:
            buy_score /= total_weight
            sell_score /= total_weight
        
        # Determine decision
        if buy_score > sell_score and buy_score >= self.min_confidence:
            decision = FinalDecision.BUY
            confidence = buy_score
        elif sell_score > buy_score and sell_score >= self.min_confidence:
            decision = FinalDecision.SELL
            confidence = sell_score
        else:
            decision = FinalDecision.HOLD
            confidence = max(buy_score, sell_score)
        
        # ===== POSITION-LEVEL SAFETY CHECKS =====
        if decision == FinalDecision.BUY:
            # Check if we can open new positions
            can_open, open_reason = safety_manager.check_can_open_position(
                portfolio_value=portfolio_value,
                holdings=holdings
            )
            
            if not can_open:
                return TradeDecision(
                    symbol=symbol,
                    decision=FinalDecision.HOLD,
                    confidence=confidence,
                    quantity=0,
                    reasoning=f"POSITION LIMIT: {open_reason}",
                    agent_signals=signals,
                    safety_blocked=True,
                    safety_reason=open_reason
                )
        
        # Calculate position size using volatility-based sizing
        quantity = self._calculate_position_size(
            decision, confidence, portfolio_value, current_price, symbol
        )
        
        # Build reasoning
        reasoning_parts = [
            f"Weighted scores - BUY: {buy_score:.2f}, SELL: {sell_score:.2f}",
            f"Decision: {decision.value} (confidence: {confidence:.2f})"
        ]
        
        for signal in signals:
            reasoning_parts.append(
                f"  {signal.agent_name}: {signal.decision.value} "
                f"({signal.confidence:.2f})"
            )
        
        return TradeDecision(
            symbol=symbol,
            decision=decision,
            confidence=confidence,
            quantity=quantity,
            reasoning="\n".join(reasoning_parts),
            agent_signals=signals
        )
    
    def _calculate_position_size(
        self,
        decision: FinalDecision,
        confidence: float,
        portfolio_value: float,
        price: float,
        symbol: str
    ) -> int:
        """Calculate position size using volatility-based sizing."""
        if decision == FinalDecision.HOLD or price <= 0:
            return 0
        
        if decision == FinalDecision.SELL:
            # For sells, use simple confidence-based sizing
            # The actual quantity will be determined by available holdings
            return 0  # Will be set by execution logic based on holdings
        
        # Use volatility-based position sizing for BUYs
        sizing = safety_manager.get_position_sizing(
            symbol=symbol,
            entry_price=price,
            portfolio_value=portfolio_value
        )
        
        # Scale by confidence (0.6 to 1.0 maps to 60% to 100% of calculated size)
        confidence_scale = (confidence - 0.4) / 0.6
        confidence_scale = max(0.5, min(1.0, confidence_scale))
        
        shares = int(sizing['shares'] * confidence_scale)
        
        return max(1, shares) if shares > 0 else 0
