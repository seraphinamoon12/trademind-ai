"""Paper trading execution engine."""
import asyncio
from typing import Optional, Dict, Any, List, Tuple
from decimal import Decimal
from datetime import datetime, timezone

from src.brokers.base import (
    BaseBroker, Order, Position, Account, OrderStatus, OrderType, OrderSide
)
from src.portfolio.manager import PortfolioManager
from src.config import settings


class PaperBroker(BaseBroker):
    """
    Paper trading broker - simulates trade execution.
    
    No real money - just tracks simulated trades.
    """
    
    def __init__(self):
        super().__init__()
        self.commission_rate = 0.001  # 0.1% per trade
        self.slippage = 0.001  # 0.1% slippage
        self._orders: Dict[str, Order] = {}
        self._positions: Dict[str, Position] = {}
        self._cash_balance = settings.starting_capital
        self._commission_paid = 0.0
    
    async def connect(self) -> None:
        """Establish connection to paper trading engine."""
        self._connected = True
    
    async def disconnect(self) -> None:
        """Close connection to paper trading engine."""
        self._connected = False
    
    async def place_order(self, order: Order) -> str:
        """Place an order and return order ID."""
        if not self.is_connected:
            raise ConnectionError("Not connected to paper broker")
        
        is_valid, message = await self.validate_order(order)
        if not is_valid:
            raise ValueError(f"Order validation failed: {message}")
        
        executed_price = order.price or 100.0
        if order.order_type == OrderType.MARKET:
            executed_price = 100.0
        elif order.order_type == OrderType.LIMIT:
            executed_price = order.price
        elif order.order_type == OrderType.STOP:
            executed_price = order.stop_price
        elif order.order_type == OrderType.STOP_LIMIT:
            executed_price = order.stop_price
        
        if order.side == OrderSide.BUY:
            executed_price = executed_price * (1 + self.slippage)
        else:
            executed_price = executed_price * (1 - self.slippage)
        
        gross_value = order.quantity * executed_price
        commission = gross_value * self.commission_rate
        self._commission_paid += commission
        
        if order.side == OrderSide.BUY:
            net_value = gross_value + commission
            self._cash_balance -= net_value
            
            if order.symbol in self._positions:
                pos = self._positions[order.symbol]
                old_cost = pos.quantity * pos.avg_cost
                pos.quantity += order.quantity
                pos.avg_cost = (old_cost + net_value) / pos.quantity
                pos.current_price = executed_price
                pos.market_value = pos.quantity * executed_price
                pos.unrealized_pnl = (executed_price - pos.avg_cost) * pos.quantity
            else:
                self._positions[order.symbol] = Position(
                    symbol=order.symbol,
                    quantity=order.quantity,
                    avg_cost=executed_price,
                    current_price=executed_price,
                    market_value=gross_value,
                    unrealized_pnl=0.0,
                    realized_pnl=0.0,
                    currency="USD"
                )
        else:
            net_value = gross_value - commission
            self._cash_balance += net_value
            
            if order.symbol in self._positions:
                pos = self._positions[order.symbol]
                pos.quantity -= order.quantity
                pos.realized_pnl += (executed_price - pos.avg_cost) * order.quantity
                pos.current_price = executed_price
                pos.market_value = pos.quantity * executed_price
                if pos.quantity == 0:
                    del self._positions[order.symbol]
                else:
                    pos.unrealized_pnl = (executed_price - pos.avg_cost) * pos.quantity
        
        order.status = OrderStatus.FILLED
        order.filled_quantity = order.quantity
        order.avg_fill_price = executed_price
        order.commission = commission
        
        self._orders[order.order_id] = order
        
        return order.order_id
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order by ID."""
        if order_id in self._orders:
            order = self._orders[order_id]
            if order.status in (OrderStatus.PENDING, OrderStatus.SUBMITTED):
                order.status = OrderStatus.CANCELLED
                return True
        return False
    
    async def get_order_status(self, order_id: str) -> OrderStatus:
        """Get status of an order."""
        if order_id in self._orders:
            return self._orders[order_id].status
        return OrderStatus.PENDING
    
    async def get_positions(self) -> List[Position]:
        """Get all current positions."""
        return list(self._positions.values())
    
    async def get_account(self) -> Account:
        """Get account information."""
        positions = await self.get_positions()
        portfolio_value = self._cash_balance + sum(p.market_value for p in positions)
        
        return Account(
            account_id="paper",
            cash_balance=self._cash_balance,
            portfolio_value=portfolio_value,
            buying_power=self._cash_balance,
            margin_available=self._cash_balance,
            total_pnl=sum(p.realized_pnl for p in positions),
            daily_pnl=0.0,
            currency="USD",
            positions=positions
        )
    
    async def get_market_price(self, symbol: str) -> float:
        """Get current market price for a symbol."""
        return 100.0
    
    async def validate_order(self, order: Order) -> Tuple[bool, str]:
        """Validate if an order can be placed."""
        if order.quantity <= 0:
            return False, "Order quantity must be positive"
        
        if order.order_type == OrderType.LIMIT and order.price is None:
            return False, "Limit orders require a price"
        
        if order.order_type == OrderType.STOP and order.stop_price is None:
            return False, "Stop orders require a stop price"
        
        if order.order_type == OrderType.STOP_LIMIT and (order.stop_price is None or order.price is None):
            return False, "Stop limit orders require both stop and limit prices"
        
        price = await self.get_market_price(order.symbol)
        total_cost = order.quantity * price * (1 + self.commission_rate)
        
        if order.side == OrderSide.BUY:
            if total_cost > self._cash_balance:
                return False, f"Insufficient cash: need ${total_cost:.2f}"
        else:
            current_qty = 0
            if order.symbol in self._positions:
                current_qty = self._positions[order.symbol].quantity
            if order.quantity > abs(current_qty):
                return False, f"Insufficient shares: have {abs(current_qty)}, need {order.quantity}"
        
        return True, "Order valid"
    
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
        
        Legacy method for backward compatibility with PortfolioManager.
        
        Returns trade details including simulated execution price.
        """
        import asyncio
        
        side = OrderSide.BUY if action == "BUY" else OrderSide.SELL
        
        order = Order(
            order_id=f"ORD_{int(datetime.now(timezone.utc).timestamp() * 1000)}",
            symbol=symbol,
            side=side,
            order_type=OrderType.MARKET,
            quantity=quantity,
            price=target_price
        )
        
        asyncio.run(self.place_order(order))
        
        executed_price = order.avg_fill_price or target_price
        
        return {
            'symbol': symbol,
            'action': action,
            'quantity': quantity,
            'target_price': target_price,
            'executed_price': round(executed_price, 2),
            'gross_value': round(quantity * executed_price, 2),
            'commission': round(order.commission or 0.0, 2),
            'net_value': round((quantity * executed_price + (order.commission or 0.0)) if action == "BUY" else (quantity * executed_price - (order.commission or 0.0)), 2),
            'status': 'FILLED',
            'slippage': self.slippage,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    def validate_order_legacy(
        self,
        symbol: str,
        action: str,
        quantity: int,
        price: float,
        portfolio: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """
        Validate if order can be executed.
        
        Legacy method for backward compatibility with PortfolioManager.
        """
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
