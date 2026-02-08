"""Strategy performance monitoring - auto-disable underperforming strategies."""
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
import logging

from src.core.database import StrategyPerformance, Trade

logger = logging.getLogger(__name__)


class StrategyMonitor:
    """
    Auto-disable underperforming strategies.
    
    Thresholds:
    - Min win rate: 30% over 20 trades
    - Min profit factor: 1.2
    - Min trades for eval: 20
    """
    
    MIN_WIN_RATE = 0.30  # 30%
    MIN_PROFIT_FACTOR = 1.2
    MIN_TRADES_FOR_EVAL = 20
    
    def evaluate_strategy(
        self, 
        strategy_name: str, 
        db: Session
    ) -> Dict[str, Any]:
        """
        Evaluate strategy performance and determine if it should continue.
        
        Args:
            strategy_name: Name of strategy to evaluate
            db: Database session
            
        Returns:
            dict: Evaluation results with keys:
                - should_run: bool
                - win_rate: float
                - profit_factor: float
                - reason: str
        """
        # Get or create performance record
        perf = db.query(StrategyPerformance).filter(
            StrategyPerformance.strategy_name == strategy_name
        ).first()
        
        if not perf:
            perf = StrategyPerformance(strategy_name=strategy_name)
            db.add(perf)
            db.commit()
        
        # Check if manually disabled
        if not perf.is_enabled:
            return {
                'should_run': False,
                'win_rate': float(perf.win_rate) if perf.win_rate else 0,
                'profit_factor': float(perf.profit_factor) if perf.profit_factor else None,
                'reason': f"Strategy manually disabled: {perf.disabled_reason}"
            }
        
        # Not enough trades yet
        if perf.total_trades < self.MIN_TRADES_FOR_EVAL:
            return {
                'should_run': True,
                'win_rate': float(perf.win_rate) if perf.win_rate else 0,
                'profit_factor': float(perf.profit_factor) if perf.profit_factor else None,
                'reason': f"Not enough trades ({perf.total_trades}/{self.MIN_TRADES_FOR_EVAL})"
            }
        
        # Calculate metrics
        win_rate = float(perf.win_rate) if perf.win_rate else 0
        profit_factor = float(perf.profit_factor) if perf.profit_factor else None
        
        # Check thresholds
        if win_rate < self.MIN_WIN_RATE:
            reason = f"Win rate {win_rate:.1%} below {self.MIN_WIN_RATE:.1%}"
            self._disable_strategy(strategy_name, reason, db)
            return {
                'should_run': False,
                'win_rate': win_rate,
                'profit_factor': profit_factor,
                'reason': reason
            }
        
        if profit_factor is not None and profit_factor < self.MIN_PROFIT_FACTOR:
            reason = f"Profit factor {profit_factor:.2f} below {self.MIN_PROFIT_FACTOR}"
            self._disable_strategy(strategy_name, reason, db)
            return {
                'should_run': False,
                'win_rate': win_rate,
                'profit_factor': profit_factor,
                'reason': reason
            }
        
        return {
            'should_run': True,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'reason': f"Win rate {win_rate:.1%}, Profit factor {profit_factor:.2f}"
        }
    
    def update_performance(self, trade: Trade, db: Session):
        """
        Update strategy performance after a trade.
        
        Args:
            trade: Completed trade
            db: Database session
        """
        if not trade.strategy:
            return
        
        perf = db.query(StrategyPerformance).filter(
            StrategyPerformance.strategy_name == trade.strategy
        ).first()
        
        if not perf:
            perf = StrategyPerformance(strategy_name=trade.strategy)
            db.add(perf)
        
        # Update trade counts
        perf.total_trades += 1
        
        # This is simplified - in reality we'd calculate realized P&L
        # For now, we'll track based on a hypothetical P&L field
        if hasattr(trade, 'realized_pnl') and trade.realized_pnl:
            pnl = float(trade.realized_pnl)
            if pnl > 0:
                perf.winning_trades += 1
                perf.gross_profit = (perf.gross_profit or 0) + pnl
            else:
                perf.losing_trades += 1
                perf.gross_loss = (perf.gross_loss or 0) + abs(pnl)
        
        perf.updated_at = datetime.utcnow()
        db.commit()
    
    def _disable_strategy(self, strategy_name: str, reason: str, db: Session):
        """Disable a strategy."""
        perf = db.query(StrategyPerformance).filter(
            StrategyPerformance.strategy_name == strategy_name
        ).first()
        
        if perf:
            perf.is_enabled = False
            perf.disabled_at = datetime.utcnow()
            perf.disabled_reason = reason
            db.commit()
        
        logger.warning(f"Strategy {strategy_name} disabled: {reason}")
    
    def enable_strategy(self, strategy_name: str, db: Session):
        """Manually re-enable a strategy."""
        perf = db.query(StrategyPerformance).filter(
            StrategyPerformance.strategy_name == strategy_name
        ).first()
        
        if perf:
            perf.is_enabled = True
            perf.disabled_at = None
            perf.disabled_reason = None
            db.commit()
            logger.info(f"Strategy {strategy_name} re-enabled")
            return True
        return False
    
    def get_all_performance(self, db: Session) -> Dict[str, Any]:
        """Get performance for all strategies."""
        perfs = db.query(StrategyPerformance).all()
        
        return {
            p.strategy_name: {
                'total_trades': p.total_trades,
                'winning_trades': p.winning_trades,
                'losing_trades': p.losing_trades,
                'win_rate': float(p.win_rate) if p.win_rate else 0,
                'profit_factor': float(p.profit_factor) if p.profit_factor else None,
                'is_enabled': p.is_enabled,
                'disabled_reason': p.disabled_reason
            }
            for p in perfs
        }


# Global strategy monitor instance
strategy_monitor = StrategyMonitor()
