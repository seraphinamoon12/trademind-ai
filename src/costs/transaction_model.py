"""Transaction cost modeling for realistic backtesting."""
from typing import Dict
import logging

logger = logging.getLogger(__name__)


class TransactionCostModel:
    """
    Model all trading costs for realistic backtesting and execution.
    
    Costs modeled:
    - Commission: $0.005 per share (e.g., IBKR), min $1.00, max 1%
    - Slippage: 0.1% for market orders
    - Spread: 0.05% (half spread on entry, half on exit)
    """
    
    COMMISSION_PER_SHARE = 0.005  # $0.005 per share (e.g., IBKR)
    MIN_COMMISSION = 1.00  # $1 minimum
    MAX_COMMISSION_PCT = 0.01  # 1% cap
    
    SLIPPAGE_PCT = 0.001  # 0.1% slippage
    SPREAD_PCT = 0.0005   # 0.05% spread (average)
    
    def calculate_cost(
        self, 
        quantity: int, 
        price: float, 
        is_market_order: bool = True
    ) -> Dict[str, float]:
        """
        Calculate total transaction cost.
        
        Args:
            quantity: Number of shares
            price: Price per share
            is_market_order: Whether this is a market order (affects slippage)
            
        Returns:
            dict: Cost breakdown with keys:
                - commission
                - slippage
                - spread
                - total
                - total_pct
        """
        notional = quantity * price
        
        if notional <= 0:
            return {
                'commission': 0.0,
                'slippage': 0.0,
                'spread': 0.0,
                'total': 0.0,
                'total_pct': 0.0
            }
        
        # Commission
        commission = max(
            quantity * self.COMMISSION_PER_SHARE,
            self.MIN_COMMISSION
        )
        commission = min(commission, notional * self.MAX_COMMISSION_PCT)
        
        # Slippage (market orders only)
        slippage = notional * self.SLIPPAGE_PCT if is_market_order else 0.0
        
        # Spread (half spread on entry, half on exit)
        spread_cost = notional * self.SPREAD_PCT
        
        total_cost = commission + slippage + spread_cost
        
        return {
            'commission': round(commission, 4),
            'slippage': round(slippage, 4),
            'spread': round(spread_cost, 4),
            'total': round(total_cost, 4),
            'total_pct': round(total_cost / notional, 6)
        }
    
    def calculate_round_trip_cost(
        self,
        quantity: int,
        entry_price: float,
        exit_price: float,
        is_market_order: bool = True
    ) -> Dict[str, float]:
        """
        Calculate total round-trip (entry + exit) costs.
        
        Args:
            quantity: Number of shares
            entry_price: Entry price
            exit_price: Exit price
            is_market_order: Whether orders are market orders
            
        Returns:
            dict: Combined cost breakdown
        """
        entry_costs = self.calculate_cost(quantity, entry_price, is_market_order)
        exit_costs = self.calculate_cost(quantity, exit_price, is_market_order)
        
        total_notional = quantity * (entry_price + exit_price)
        total_cost = entry_costs['total'] + exit_costs['total']
        
        return {
            'entry': entry_costs,
            'exit': exit_costs,
            'commission': entry_costs['commission'] + exit_costs['commission'],
            'slippage': entry_costs['slippage'] + exit_costs['slippage'],
            'spread': entry_costs['spread'] + exit_costs['spread'],
            'total': round(total_cost, 4),
            'total_pct': round(total_cost / (quantity * entry_price), 6)
        }
    
    def estimate_break_even(
        self,
        quantity: int,
        entry_price: float,
        is_market_order: bool = True
    ) -> float:
        """
        Calculate the price movement needed to break even.
        
        Args:
            quantity: Number of shares
            entry_price: Entry price
            is_market_order: Whether orders are market orders
            
        Returns:
            float: Percentage gain needed to break even
        """
        # Assume exit at same price as entry for estimation
        costs = self.calculate_round_trip_cost(
            quantity, entry_price, entry_price, is_market_order
        )
        
        notional = quantity * entry_price
        break_even_pct = costs['total'] / notional
        
        return round(break_even_pct, 6)


# Global cost model instance
cost_model = TransactionCostModel()
