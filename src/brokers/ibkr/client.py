"""Interactive Brokers broker implementation using ib_insync."""
import asyncio
from typing import Optional, List, Dict, Any, Tuple
import logging

try:
    from ib_insync import IB, Stock, MarketOrder, LimitOrder, StopOrder, StopLimitOrder
except ImportError:
    IB = None
    Stock = None
    MarketOrder = None
    LimitOrder = None
    StopOrder = None
    StopLimitOrder = None

from src.brokers.base import (
    BaseBroker, Order, Position, Account,
    OrderStatus, OrderType, OrderSide
)

logger = logging.getLogger(__name__)


class IBKRBroker(BaseBroker):
    """Interactive Brokers broker implementation."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 7497,
        client_id: int = 1,
        account: Optional[str] = None,
        paper_trading: bool = True
    ):
        super().__init__()
        self.host = host
        self.port = port
        self.client_id = client_id
        self.account = account
        self.paper_trading = paper_trading
        self.exchange = "SMART"
        self.currency = "USD"
        self.market_data_timeout = 0.1

        if IB is None:
            raise ImportError(
                "ib_insync is not installed. Please install it with: pip install ib_insync>=0.9.86"
            )

        self.ib = IB()
        self._orders: Dict[str, Order] = {}

    async def connect(self) -> None:
        """Establish connection to IBKR TWS or Gateway."""
        try:
            await self.ib.connectAsync(
                host=self.host,
                port=self.port,
                clientId=self.client_id,
                timeout=10
            )
            self._connected = True

            managed_accounts = self.ib.managedAccounts()
            account_id = self.account or (managed_accounts[0] if managed_accounts else None)
            if account_id:
                await self.ib.reqAccountSummaryAsync()
                logger.info(f"Connected to IBKR account: {account_id}")
            else:
                logger.warning("Connected to IBKR but no account ID found")

        except Exception as e:
            logger.error(f"Failed to connect to IBKR: {e}")
            self._connected = False
            raise

    async def disconnect(self) -> None:
        """Close connection to IBKR."""
        if self._connected:
            await self.ib.disconnectAsync()
            self._connected = False
            logger.info("Disconnected from IBKR")

    async def place_order(self, order: Order) -> str:
        """Place an order and return order ID."""
        if not self.is_connected:
            raise ConnectionError("Not connected to IBKR")

        contract = Stock(order.symbol, self.exchange, self.currency)

        if order.order_type == OrderType.MARKET:
            ib_order = MarketOrder(order.side.value, order.quantity)
        elif order.order_type == OrderType.LIMIT:
            ib_order = LimitOrder(order.side.value, order.quantity, order.price)
        elif order.order_type == OrderType.STOP:
            ib_order = StopOrder(order.side.value, order.quantity, order.stop_price)
        elif order.order_type == OrderType.STOP_LIMIT:
            ib_order = StopLimitOrder(order.side.value, order.quantity, order.stop_price, order.price)
        else:
            raise ValueError(f"Unsupported order type: {order.order_type}")

        trade = await self.ib.placeOrderAsync(contract, ib_order)

        if trade.orderStatus and trade.orderStatus.orderId:
            order.order_id = str(trade.orderStatus.orderId)
            order.status = self._map_ib_order_status(trade.orderStatus.status)
            self._orders[order.order_id] = order
            logger.info(f"Placed order {order.order_id} for {order.symbol}")
            return order.order_id

        raise RuntimeError(f"Failed to place order for {order.symbol}")

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order by ID."""
        if not self.is_connected:
            raise ConnectionError("Not connected to IBKR")

        if order_id not in self._orders:
            logger.warning(f"Order {order_id} not found")
            return False

        order = self._orders[order_id]
        ib_order_id = int(order_id)

        try:
            trade = await self.ib.cancelOrderAsync(ib_order_id)
            await asyncio.sleep(0.1)
            if trade and trade.orderStatus:
                order.status = self._map_ib_order_status(trade.orderStatus.status)
            else:
                order.status = OrderStatus.CANCELLED
            logger.info(f"Cancelled order {order_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            return False

    async def get_order_status(self, order_id: str) -> OrderStatus:
        """Get status of an order."""
        if order_id in self._orders:
            return self._orders[order_id].status

        logger.warning(f"Order {order_id} not found")
        return OrderStatus.PENDING

    async def get_positions(self) -> List[Position]:
        """Get all current positions."""
        if not self.is_connected:
            raise ConnectionError("Not connected to IBKR")

        positions = []
        for pos in self.ib.positions():
            symbol = pos.contract.symbol
            quantity = pos.position
            avg_cost = pos.avgCost
            market_price = pos.marketPrice()
            market_value = abs(quantity * market_price)
            unrealized_pnl = (market_price - avg_cost) * quantity

            positions.append(Position(
                symbol=symbol,
                quantity=int(quantity),
                avg_cost=avg_cost,
                current_price=market_price,
                market_value=market_value,
                unrealized_pnl=unrealized_pnl
            ))

        return positions

    async def get_account(self) -> Account:
        """Get account information."""
        if not self.is_connected:
            raise ConnectionError("Not connected to IBKR")

        summary = self.ib.accountSummary()
        account_values = {}

        for item in summary:
            tag = item.tag
            value = item.value
            if value:
                try:
                    account_values[tag] = float(value)
                except ValueError:
                    pass

        managed_accounts = self.ib.managedAccounts()
        account_id = self.account or (managed_accounts[0] if managed_accounts else "unknown")

        return Account(
            account_id=account_id,
            cash_balance=account_values.get('TotalCashBalance', 0.0),
            portfolio_value=account_values.get('NetLiquidation', 0.0),
            buying_power=account_values.get('BuyingPower', 0.0),
            margin_available=account_values.get('AvailableFunds', 0.0),
            total_pnl=account_values.get('RealizedPnL', 0.0),
            daily_pnl=account_values.get('NetLiquidationByCurrency', 0.0) - account_values.get('PreviousEquityWithLoanValue', 0.0),
            currency=self.currency,
            positions=await self.get_positions()
        )

    async def get_market_price(self, symbol: str) -> float:
        """Get current market price for a symbol."""
        if not self.is_connected:
            raise ConnectionError("Not connected to IBKR")

        contract = Stock(symbol, self.exchange, self.currency)
        ticker = await self.ib.reqMktDataAsync(contract)

        await asyncio.sleep(self.market_data_timeout)

        price = ticker.marketPrice()
        if price is None:
            price = ticker.last
        if price is None:
            price = ticker.close

        if price is None:
            raise ValueError(f"Unable to get market price for {symbol}")

        return float(price)

    async def validate_order(self, order: Order) -> Tuple[bool, str]:
        """Validate if an order can be placed."""
        if not self.is_connected:
            return False, "Not connected to IBKR"

        if order.quantity <= 0:
            return False, "Order quantity must be positive"

        if order.order_type == OrderType.LIMIT and order.price is None:
            return False, "Limit orders require a price"

        if order.order_type == OrderType.STOP and order.stop_price is None:
            return False, "Stop orders require a stop price"

        if order.order_type == OrderType.STOP_LIMIT and (order.stop_price is None or order.price is None):
            return False, "Stop limit orders require both stop and limit prices"

        try:
            price = await self.get_market_price(order.symbol)
            total_value = order.quantity * price

            account = await self.get_account()

            if order.side == OrderSide.BUY:
                if total_value > account.buying_power:
                    return False, f"Insufficient buying power: need ${total_value:.2f}"
            else:
                positions = await self.get_positions()
                current_qty = next((p.quantity for p in positions if p.symbol == order.symbol), 0)
                if order.quantity > abs(current_qty):
                    return False, f"Insufficient shares: have {abs(current_qty)}, need {order.quantity}"

        except Exception as e:
            return False, f"Validation error: {str(e)}"

        return True, "Order valid"

    def _map_ib_order_status(self, status: str) -> OrderStatus:
        """Map IB order status to internal OrderStatus enum."""
        status_map = {
            'PendingSubmit': OrderStatus.PENDING,
            'PendingCancel': OrderStatus.PENDING,
            'PreSubmitted': OrderStatus.SUBMITTED,
            'Submitted': OrderStatus.SUBMITTED,
            'ApiPending': OrderStatus.SUBMITTED,
            'ApiCancelled': OrderStatus.CANCELLED,
            'Cancelled': OrderStatus.CANCELLED,
            'Filled': OrderStatus.FILLED,
            'PartiallyFilled': OrderStatus.PARTIAL,
            'Inactive': OrderStatus.REJECTED,
        }
        return status_map.get(status, OrderStatus.PENDING)
