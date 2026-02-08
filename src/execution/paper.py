"""Paper trading execution engine."""
from typing import Optional, Dict, Any
from decimal import Decimal

from src.portfolio.manager import PortfolioManager
from src.config import settings


class PaperBroker:
    """
    Paper trading broker - simulates trade execution.
    
    No real money - just tracks simulated trades.
    """
    
    def __init__(self):
        self.commission_rate = 0.001  # 0.1% per trade
        self.slippage = 0.001  # 0.1% slippage
    
    def execute(
        self,
        symbol: str,
        action: str,
        quantity: int,
        target_price: float,
        portfolio_manager: PortfolioManager
    ) -> Dict[str, Any]:
        """
        Execute a paper trade with slippage simulation.
        
        Returns trade details including simulated execution price.
        """
        # Simulate slippage (price moves against us)
        if action == "BUY":
            executed_price = target_price * (1 + self.slippage)
        else:
            executed_price = target_price * (1 - self.slippage)
        
        gross_value = quantity * executed_price
        commission = gross_value * self.commission_rate
        net_value = gross_value + commission if action == "BUY" else gross_value - commission
        
        return {
            'symbol': symbol,
            'action': action,
            'quantity': quantity,
            'target_price': target_price,
            'executed_price': round(executed_price, 2),
            'gross_value': round(gross_value, 2),
            'commission': round(commission, 2),
            'net_value': round(net_value, 2),
            'status': 'FILLED',
            'slippage': self.slippage,
            'timestamp': None  # Will be set on execution
        }
    
    def validate_order(
        self,
        symbol: str,
        action: str,
        quantity: int,
        price: float,
        portfolio: Dict[str, Any]
    ) -> tuple[bool, str]:
        """Validate if order can be executed."""
        total_cost = quantity * price * (1 + self.commission_rate)
        
        if action == "BUY":
            if total_cost > portfolio.get('cash_balance', 0):
                return False, f"Insufficient cash: need ${total_cost:.2f}"
        
        elif action == "SELL":
            holdings = portfolio.get('holdings', {})
            current_qty = holdings.get(symbol, {}).get('quantity', 0)
            if quantity > current_qty:
                return False, f"Insufficient shares: have {current_qty}, need {quantity}"
        
        return True, "Order valid"
