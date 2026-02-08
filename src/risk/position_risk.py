"""Position risk management - max positions, portfolio heat tracking."""
from typing import Tuple, Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class PositionRiskManager:
    """
    Manage position count limits and portfolio heat (total risk at risk).
    
    Prevents scenario: 10 positions × 10% each = 100% capital deployed.
    
    Key Limits:
    - MAX_OPEN_POSITIONS = 5 (prevent overexposure)
    - PORTFOLIO_HEAT_MAX_PCT = 10% (max capital at risk)
    - MAX_POSITION_PCT = 10% (hard ceiling per position)
    """
    
    MAX_OPEN_POSITIONS = 5
    MAX_POSITION_PCT = 0.10      # 10% max per position (hard ceiling)
    PORTFOLIO_HEAT_MAX_PCT = 0.10  # 10% of capital at risk
    
    def __init__(self):
        self.symbol_to_stop_pct: Dict[str, float] = {}
    
    def can_open_position(
        self, 
        open_positions: int,
        portfolio_value: float,
        new_position_risk: float,
        current_heat: float = None,
        holdings: Dict[str, Any] = None
    ) -> Tuple[bool, str]:
        """
        Check if a new position can be opened.
        
        Args:
            open_positions: Number of currently open positions
            portfolio_value: Total portfolio value
            new_position_risk: Dollar amount at risk (position_value × stop_loss_pct)
            current_heat: Pre-calculated portfolio heat (optional)
            holdings: Current holdings data (optional)
            
        Returns:
            Tuple[bool, str]: (can_open, reason)
        """
        # Check position count
        if open_positions >= self.MAX_OPEN_POSITIONS:
            return False, f"Max open positions ({self.MAX_OPEN_POSITIONS}) reached"
        
        # Check portfolio heat
        if current_heat is None and holdings:
            current_heat = self.calculate_portfolio_heat(holdings)
        
        if current_heat is not None:
            max_heat = self.PORTFOLIO_HEAT_MAX_PCT * portfolio_value
            if current_heat + new_position_risk > max_heat:
                return False, (
                    f"Portfolio heat would exceed {self.PORTFOLIO_HEAT_MAX_PCT:.0%} limit "
                    f"(${current_heat + new_position_risk:.2f} > ${max_heat:.2f})"
                )
        
        return True, "OK"
    
    def calculate_portfolio_heat(self, holdings: Dict[str, Any]) -> float:
        """
        Calculate total risk if all stops are hit.
        
        Heat = sum of (position_value × stop_loss_pct) for all positions.
        
        Args:
            holdings: Dict of holdings with keys like:
                - market_value: Position dollar value
                - stop_loss_pct: Stop loss percentage (defaults to 5%)
                
        Returns:
            float: Total portfolio heat in dollars
        """
        total_heat = 0.0
        
        for symbol, holding in holdings.items():
            if not isinstance(holding, dict):
                continue
                
            position_value = holding.get('market_value', 0)
            stop_loss_pct = holding.get('stop_loss_pct', 0.05)  # Default 5%
            
            if position_value > 0:
                position_heat = position_value * stop_loss_pct
                total_heat += position_heat
        
        return total_heat
    
    def get_heat_status(
        self, 
        holdings: Dict[str, Any], 
        portfolio_value: float
    ) -> Dict[str, Any]:
        """
        Get current heat status for monitoring.
        
        Returns:
            dict: Heat status with keys:
                - heat_dollars: Total heat in dollars
                - heat_pct: Heat as percentage of portfolio
                - limit_dollars: Max allowed heat
                - limit_pct: Max heat percentage
                - remaining: Remaining heat capacity
                - status: 'ok', 'warning', or 'danger'
                - open_positions: Number of open positions
        """
        heat = self.calculate_portfolio_heat(holdings)
        heat_pct = heat / portfolio_value if portfolio_value > 0 else 0
        limit_dollars = self.PORTFOLIO_HEAT_MAX_PCT * portfolio_value
        limit_pct = self.PORTFOLIO_HEAT_MAX_PCT
        
        # Determine status
        if heat_pct >= self.PORTFOLIO_HEAT_MAX_PCT:
            status = 'danger'
        elif heat_pct >= self.PORTFOLIO_HEAT_MAX_PCT * 0.8:
            status = 'warning'
        else:
            status = 'ok'
        
        return {
            'heat_dollars': heat,
            'heat_pct': heat_pct,
            'limit_dollars': limit_dollars,
            'limit_pct': limit_pct,
            'remaining': limit_dollars - heat,
            'remaining_pct': limit_pct - heat_pct,
            'status': status,
            'open_positions': len(holdings),
            'max_positions': self.MAX_OPEN_POSITIONS
        }
    
    def check_position_size(
        self, 
        position_value: float, 
        portfolio_value: float
    ) -> Tuple[bool, str]:
        """
        Check if position size is within limits.
        
        Args:
            position_value: Dollar value of position
            portfolio_value: Total portfolio value
            
        Returns:
            Tuple[bool, str]: (is_valid, reason)
        """
        if portfolio_value <= 0:
            return False, "Invalid portfolio value"
        
        position_pct = position_value / portfolio_value
        
        if position_pct > self.MAX_POSITION_PCT:
            return False, (
                f"Position size {position_pct:.1%} exceeds "
                f"max {self.MAX_POSITION_PCT:.0%}"
            )
        
        return True, "OK"
    
    def get_position_status(
        self, 
        holdings: Dict[str, Any],
        portfolio_value: float
    ) -> Dict[str, Any]:
        """
        Get comprehensive position status.
        
        Returns:
            dict: Complete position and heat status
        """
        heat_status = self.get_heat_status(holdings, portfolio_value)
        
        # Count open positions
        open_count = len(holdings)
        can_add_new = open_count < self.MAX_OPEN_POSITIONS
        
        return {
            'open_positions': open_count,
            'max_positions': self.MAX_OPEN_POSITIONS,
            'can_open_new': can_add_new and heat_status['status'] != 'danger',
            'position_limit_remaining': self.MAX_OPEN_POSITIONS - open_count,
            'heat': heat_status,
            'max_position_pct': self.MAX_POSITION_PCT
        }


# Global position risk manager instance
position_risk_manager = PositionRiskManager()
