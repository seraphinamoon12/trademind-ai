"""Circuit Breaker - Global trading halt mechanism."""
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """
    Global circuit breaker for trading system.
    
    Implements tiered drawdown protection:
    - Warning at -10% drawdown
    - Halt at -15% drawdown
    - Daily loss limit at -3%
    - Consecutive loss limit (5 losses)
    """
    
    # Tiered drawdown thresholds
    DRAWDOWN_WARNING_PCT = 0.10   # 10% - warning only
    DRAWDOWN_HALT_PCT = 0.15      # 15% - halt trading
    
    # Daily loss limit
    DAILY_LOSS_LIMIT_PCT = 0.03   # 3%
    
    # Consecutive losses
    CONSECUTIVE_LOSS_LIMIT = 5
    
    # Kill switch file path
    KILL_SWITCH_FILE = "/tmp/trading_stop"
    
    def __init__(self):
        self.is_halted = False
        self.halt_reason: Optional[str] = None
        self.halt_time: Optional[datetime] = None
        self.warning_issued = False
        self.peak_value: float = 0.0
        
    def check_can_trade(
        self, 
        portfolio_value: float,
        daily_pnl: float,
        daily_pnl_pct: float,
        recent_trades: list = None
    ) -> bool:
        """
        Check if trading is allowed.
        
        Args:
            portfolio_value: Current portfolio value
            daily_pnl: Daily P&L in dollars
            daily_pnl_pct: Daily P&L as percentage
            recent_trades: List of recent trades for consecutive loss check
            
        Returns:
            bool: True if trading is allowed
        """
        # Check kill switch file
        if self._check_kill_switch_file():
            self.trigger_circuit_breaker("Kill switch file detected")
            return False
        
        # Already halted
        if self.is_halted:
            return False
        
        # Update peak value for drawdown calculation
        if portfolio_value > self.peak_value:
            self.peak_value = portfolio_value
            self.warning_issued = False  # Reset warning on new high
        
        # Calculate drawdown
        drawdown = 0.0
        if self.peak_value > 0:
            drawdown = (self.peak_value - portfolio_value) / self.peak_value
        
        # Check daily loss limit
        if daily_pnl_pct < -self.DAILY_LOSS_LIMIT_PCT:
            self.trigger_circuit_breaker(
                f"Daily loss limit hit: {daily_pnl_pct:.2%} (limit: -{self.DAILY_LOSS_LIMIT_PCT:.0%})"
            )
            return False
        
        # Check tiered drawdown
        if drawdown >= self.DRAWDOWN_HALT_PCT:
            self.trigger_circuit_breaker(
                f"Max drawdown exceeded: {drawdown:.2%} (halt at {self.DRAWDOWN_HALT_PCT:.0%})"
            )
            return False
        elif drawdown >= self.DRAWDOWN_WARNING_PCT:
            if not self.warning_issued:
                logger.warning(
                    f"⚠️ DRAWDOWN WARNING: {drawdown:.2%} "
                    f"(halt threshold: {self.DRAWDOWN_HALT_PCT:.0%})"
                )
                self.warning_issued = True
                # Alert will be sent by alert manager
        
        # Check consecutive losses
        if recent_trades:
            consecutive_losses = self._count_consecutive_losses(recent_trades)
            if consecutive_losses >= self.CONSECUTIVE_LOSS_LIMIT:
                self.trigger_circuit_breaker(
                    f"{consecutive_losses} consecutive losses"
                )
                return False
        
        return True
    
    def trigger_circuit_breaker(self, reason: str):
        """Trigger circuit breaker and halt all trading."""
        self.is_halted = True
        self.halt_reason = reason
        self.halt_time = datetime.utcnow()
        
        logger.critical(f"🚨 CIRCUIT BREAKER TRIGGERED: {reason}")
        logger.info("Trading halted - positions remain open for manual review")
        
        # Publish event for alerting
        try:
            from src.core.events import event_bus, Events
            event_bus.publish(Events.CIRCUIT_BREAKER, {
                'reason': reason,
                'timestamp': self.halt_time.isoformat(),
                'portfolio_value': self.peak_value * (1 - self.DRAWDOWN_WARNING_PCT) if self.peak_value > 0 else 0
            })
        except ImportError:
            pass
    
    def reset(self, reset_by: str = "manual") -> bool:
        """Reset circuit breaker (requires manual intervention)."""
        if not self.is_halted:
            return False
        
        logger.info(f"🟢 Circuit breaker reset by {reset_by}")
        logger.info(f"   Previous halt reason: {self.halt_reason}")
        logger.info(f"   Halted for: {(datetime.utcnow() - self.halt_time).total_seconds() / 60:.1f} minutes")
        
        self.is_halted = False
        self.halt_reason = None
        self.halt_time = None
        self.warning_issued = False
        self.peak_value = 0.0  # Reset peak for new calculation
        
        # Remove kill switch file if exists
        if Path(self.KILL_SWITCH_FILE).exists():
            Path(self.KILL_SWITCH_FILE).unlink()
        
        return True
    
    def _count_consecutive_losses(self, trades: list) -> int:
        """Count consecutive losing trades from most recent."""
        consecutive = 0
        for trade in reversed(trades):
            # Check if trade has P&L (closed trade)
            if hasattr(trade, 'realized_pnl'):
                if trade.realized_pnl < 0:
                    consecutive += 1
                else:
                    break
            elif hasattr(trade, 'pnl'):
                if trade.pnl < 0:
                    consecutive += 1
                else:
                    break
            else:
                break
        return consecutive
    
    def _check_kill_switch_file(self) -> bool:
        """Check for emergency stop file."""
        return Path(self.KILL_SWITCH_FILE).exists()
    
    def get_status(self) -> Dict[str, Any]:
        """Get current circuit breaker status."""
        return {
            'is_halted': self.is_halted,
            'halt_reason': self.halt_reason,
            'halt_time': self.halt_time.isoformat() if self.halt_time else None,
            'warning_issued': self.warning_issued,
            'drawdown_warning_pct': self.DRAWDOWN_WARNING_PCT,
            'drawdown_halt_pct': self.DRAWDOWN_HALT_PCT,
            'daily_loss_limit_pct': self.DAILY_LOSS_LIMIT_PCT,
            'consecutive_loss_limit': self.CONSECUTIVE_LOSS_LIMIT,
            'peak_value': self.peak_value,
            'kill_switch_file': self.KILL_SWITCH_FILE,
            'kill_switch_active': self._check_kill_switch_file()
        }


# Global circuit breaker instance
circuit_breaker = CircuitBreaker()
