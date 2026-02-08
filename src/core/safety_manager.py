"""Safety Manager - Coordinates all safety components."""
from datetime import datetime
from typing import Tuple, Dict, Any, Optional
import logging

from src.core.circuit_breaker import circuit_breaker, CircuitBreaker
from src.core.time_filter import time_filter, TimeFilter
from src.risk.position_risk import position_risk_manager, PositionRiskManager
from src.risk.position_sizer import position_sizer, VolatilityPositionSizer

logger = logging.getLogger(__name__)


class SafetyManager:
    """
    Central safety coordinator for the trading system.
    
    Orchestrates:
    - Circuit breaker (drawdown, daily loss limits)
    - Time restrictions (market hours, cutoff times)
    - Position limits (max 5 positions)
    - Portfolio heat tracking (max 10% at risk)
    - Position sizing (volatility-based ATR)
    
    Usage:
        safety = SafetyManager()
        can_trade, reason = safety.check_can_trade(portfolio_data)
        if can_trade:
            sizing = safety.get_position_sizing(symbol, entry_price, portfolio_value)
    """
    
    def __init__(
        self,
        circuit_breaker: CircuitBreaker = None,
        time_filter: TimeFilter = None,
        position_risk: PositionRiskManager = None,
        position_sizer: VolatilityPositionSizer = None
    ):
        self.circuit_breaker = circuit_breaker or CircuitBreaker()
        self.time_filter = time_filter or TimeFilter()
        self.position_risk = position_risk or PositionRiskManager()
        self.position_sizer = position_sizer or VolatilityPositionSizer()
        
        # Audit log of safety decisions
        self.decision_log: list = []
    
    def check_can_trade(
        self,
        portfolio_value: float,
        daily_pnl: float = 0,
        daily_pnl_pct: float = 0,
        recent_trades: list = None
    ) -> Tuple[bool, str]:
        """
        Global check if trading is allowed at all.
        
        Args:
            portfolio_value: Current portfolio value
            daily_pnl: Daily P&L in dollars
            daily_pnl_pct: Daily P&L as percentage
            recent_trades: Recent trades for consecutive loss check
            
        Returns:
            Tuple[bool, str]: (can_trade, reason)
        """
        # 1. Check circuit breaker
        can_trade = self.circuit_breaker.check_can_trade(
            portfolio_value=portfolio_value,
            daily_pnl=daily_pnl,
            daily_pnl_pct=daily_pnl_pct,
            recent_trades=recent_trades
        )
        
        if not can_trade:
            reason = f"Circuit breaker: {self.circuit_breaker.halt_reason}"
            self._log_decision("global_check", False, reason)
            return False, reason
        
        # 2. Check market hours
        market_status = self.time_filter.get_market_status()
        if not market_status['is_market_open']:
            reason = f"Market is closed"
            self._log_decision("global_check", False, reason)
            return False, reason
        
        self._log_decision("global_check", True, "All checks passed")
        return True, "OK"
    
    def check_can_open_position(
        self,
        portfolio_value: float,
        holdings: Dict[str, Any],
        new_position_risk: float = 0
    ) -> Tuple[bool, str]:
        """
        Check if a new position can be opened.
        
        Args:
            portfolio_value: Total portfolio value
            holdings: Current holdings dict
            new_position_risk: Dollar risk of proposed position
            
        Returns:
            Tuple[bool, str]: (can_open, reason)
        """
        # 1. Check circuit breaker
        if self.circuit_breaker.is_halted:
            reason = f"Circuit breaker active: {self.circuit_breaker.halt_reason}"
            self._log_decision("open_position", False, reason)
            return False, reason
        
        # 2. Check time restrictions
        can_trade_time, time_reason = self.time_filter.can_open_new_position()
        if not can_trade_time:
            self._log_decision("open_position", False, time_reason)
            return False, time_reason
        
        # 3. Check position limits and heat
        open_count = len(holdings)
        can_open, reason = self.position_risk.can_open_position(
            open_positions=open_count,
            portfolio_value=portfolio_value,
            new_position_risk=new_position_risk,
            holdings=holdings
        )
        
        self._log_decision("open_position", can_open, reason)
        return can_open, reason
    
    def check_can_close_position(self) -> Tuple[bool, str]:
        """Check if positions can be closed."""
        # 1. Check circuit breaker (allow closing even if halted)
        # but check kill switch
        if self.circuit_breaker._check_kill_switch_file():
            return False, "Kill switch active"
        
        # 2. Check market is open
        can_close, reason = self.time_filter.can_close_position()
        return can_close, reason
    
    def get_position_sizing(
        self,
        symbol: str,
        entry_price: float,
        portfolio_value: float,
        atr: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Get volatility-based position sizing.
        
        Args:
            symbol: Stock symbol
            entry_price: Proposed entry price
            portfolio_value: Total portfolio value
            atr: Optional pre-calculated ATR
            
        Returns:
            dict: Position sizing details
        """
        sizing = self.position_sizer.calculate_position_size(
            portfolio_value=portfolio_value,
            symbol=symbol,
            entry_price=entry_price,
            atr=atr
        )
        
        # Check if sizing exceeds position limits
        is_valid, reason = self.position_risk.check_position_size(
            position_value=sizing['position_value'],
            portfolio_value=portfolio_value
        )
        
        sizing['valid'] = is_valid
        sizing['validation_reason'] = reason
        
        return sizing
    
    def get_portfolio_heat_status(
        self,
        holdings: Dict[str, Any],
        portfolio_value: float
    ) -> Dict[str, Any]:
        """Get comprehensive portfolio heat status."""
        return self.position_risk.get_position_status(holdings, portfolio_value)
    
    def emergency_stop(self, reason: str, triggered_by: str = "manual"):
        """
        Trigger emergency stop.
        
        Args:
            reason: Why the stop was triggered
            triggered_by: Who/what triggered it
        """
        full_reason = f"EMERGENCY STOP by {triggered_by}: {reason}"
        logger.critical(full_reason)
        self.circuit_breaker.trigger_circuit_breaker(full_reason)
        self._log_decision("emergency_stop", False, full_reason)
    
    def reset_circuit_breaker(self, reset_by: str = "manual") -> bool:
        """Reset circuit breaker (manual intervention required)."""
        return self.circuit_breaker.reset(reset_by)
    
    def get_safety_status(
        self,
        portfolio_value: float = None,
        holdings: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Get complete safety status.
        
        Returns:
            dict: All safety system statuses
        """
        status = {
            'circuit_breaker': self.circuit_breaker.get_status(),
            'market': self.time_filter.get_market_status(),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        if holdings and portfolio_value:
            status['portfolio'] = self.get_portfolio_heat_status(holdings, portfolio_value)
        
        # Overall safety summary
        cb = status['circuit_breaker']
        market = status['market']
        
        status['summary'] = {
            'can_trade': (
                not cb['is_halted'] and 
                market['is_market_open']
            ),
            'can_open_new': (
                not cb['is_halted'] and 
                market['can_open_new_position']
            ),
            'safety_status': 'danger' if cb['is_halted'] else 
                           'warning' if cb['warning_issued'] else 
                           'ok'
        }
        
        return status
    
    def _log_decision(self, check_type: str, allowed: bool, reason: str):
        """Log safety decision for audit trail."""
        decision = {
            'timestamp': datetime.utcnow().isoformat(),
            'check_type': check_type,
            'allowed': allowed,
            'reason': reason
        }
        self.decision_log.append(decision)
        
        # Keep log from growing too large
        if len(self.decision_log) > 1000:
            self.decision_log = self.decision_log[-500:]
    
    def get_decision_log(self, limit: int = 100) -> list:
        """Get recent safety decisions."""
        return self.decision_log[-limit:]


# Global safety manager instance
safety_manager = SafetyManager()
