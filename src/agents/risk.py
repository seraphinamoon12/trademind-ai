"""Risk Management Agent."""
import pandas as pd
from typing import Optional, Dict, Any

from src.agents.base import BaseAgent, AgentSignal, AgentDecision
from src.config import settings
from src.filters.liquidity import liquidity_filter
from src.filters.earnings import earnings_filter
from src.risk.sector_monitor import sector_monitor
from src.risk.position_sizer import position_sizer


class RiskAgent(BaseAgent):
    """
    Risk Management Agent.
    
    Validates trades against risk rules including:
    - Liquidity filters (volume, price, spread)
    - Earnings filter (avoid trading around earnings)
    - Sector concentration limits
    - Position size limits
    """
    
    name = "risk"
    weight = settings.risk_weight
    can_veto = True
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.max_position_pct = kwargs.get('max_position_pct', settings.max_position_pct)
        self.stop_loss_pct = kwargs.get('stop_loss_pct', settings.stop_loss_pct)
        self.take_profit_pct = kwargs.get('take_profit_pct', settings.take_profit_pct)
        self.max_daily_loss_pct = kwargs.get('max_daily_loss_pct', settings.max_daily_loss_pct)
    
    async def analyze(
        self, 
        symbol: str, 
        data: pd.DataFrame,
        portfolio_value: float = 100000,
        current_holdings: Dict[str, Any] = None,
        daily_pnl: float = 0,
        **context
    ) -> AgentSignal:
        """Analyze risk and return approval/veto decision."""
        
        current_holdings = current_holdings or {}
        violations = []
        warnings = []
        
        # ===== LIQUIDITY FILTER =====
        liquid, liquid_reason = liquidity_filter.validate(symbol)
        if not liquid:
            violations.append(f"Liquidity: {liquid_reason}")
        
        # ===== EARNINGS FILTER =====
        safe_from_earnings = earnings_filter.is_safe_to_trade(symbol)
        if not safe_from_earnings:
            warnings.append("Earnings announcement soon")
        
        # ===== SECTOR CONCENTRATION =====
        can_add_sector, sector_reason = sector_monitor.can_add_to_sector(
            holdings=current_holdings,
            symbol=symbol,
            portfolio_value=portfolio_value
        )
        if not can_add_sector:
            violations.append(f"Sector: {sector_reason}")
        
        # ===== POSITION SIZE CHECK =====
        symbol_value = current_holdings.get(symbol, {}).get('market_value', 0)
        position_pct = symbol_value / portfolio_value if portfolio_value > 0 else 0
        
        if position_pct > self.max_position_pct:
            violations.append(
                f"Position size exceeds limit: {position_pct:.1%} "
                f"(max: {self.max_position_pct:.1%})"
            )
        
        # ===== PORTFOLIO EXPOSURE =====
        total_exposure = sum(
            h.get('market_value', 0) 
            for h in current_holdings.values()
        )
        exposure_pct = total_exposure / portfolio_value if portfolio_value > 0 else 0
        
        if exposure_pct > 0.9:  # 90% invested
            warnings.append(f"High portfolio exposure: {exposure_pct:.1%}")
        
        # Calculate position size recommendation (volatility-based)
        atr = position_sizer.calculate_atr_from_data(data) if data is not None else None
        recommended_size = self._calculate_position_size(
            portfolio_value, atr, price=data['close'].iloc[-1] if data is not None else None
        )
        
        # Determine decision
        if violations:
            return AgentSignal(
                agent_name=self.name,
                symbol=symbol,
                decision=AgentDecision.VETO,
                confidence=0.95,
                reasoning="RISK VIOLATIONS: " + "; ".join(violations),
                data={
                    'violations': violations,
                    'warnings': warnings,
                    'position_pct': position_pct,
                    'recommended_size': recommended_size,
                    'liquidity_passed': liquid,
                    'earnings_safe': safe_from_earnings,
                    'sector_ok': can_add_sector
                }
            )
        
        # Build reasoning
        reasoning_parts = ["Risk check passed."]
        if warnings:
            reasoning_parts.append("Warnings: " + "; ".join(warnings))
        reasoning_parts.append(f"Position: {position_pct:.1%} of portfolio")
        reasoning_parts.append(f"Recommended size: {recommended_size} shares")
        
        return AgentSignal(
            agent_name=self.name,
            symbol=symbol,
            decision=AgentDecision.HOLD,  # Risk agent doesn't generate trades
            confidence=0.8,
            reasoning=" ".join(reasoning_parts),
            data={
                'warnings': warnings,
                'position_pct': position_pct,
                'recommended_size': recommended_size,
                'atr': atr,
                'liquidity_passed': liquid,
                'earnings_safe': safe_from_earnings,
                'sector_ok': can_add_sector
            }
        )
    
    def _calculate_position_size(
        self,
        portfolio_value: float,
        atr: Optional[float],
        price: Optional[float]
    ) -> int:
        """Calculate recommended position size using VolatilityPositionSizer."""
        if price is None or price <= 0:
            return 0

        sizing_result = position_sizer.calculate_position_size(
            portfolio_value=portfolio_value,
            symbol='',  # Symbol not needed if ATR is provided
            entry_price=price,
            atr=atr
        )

        return sizing_result.get('shares', 0)
