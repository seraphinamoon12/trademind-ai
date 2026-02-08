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
        self._tickers: Dict[str, Any] = {}
        self._account_values: Dict[str, Any] = {}

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

            self._setup_order_callbacks()
            self._setup_position_callbacks()
            self._setup_account_callbacks()

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

    async def get_orders(self, status: Optional[str] = None) -> List[Order]:
        """
        Get orders with optional status filtering.

        Args:
            status: Filter by status - "open", "filled", "cancelled", or None for all

        Returns:
            List of Order objects
        """
        if not self.is_connected:
            raise ConnectionError("Not connected to IBKR")

        orders = []
        for trade in self.ib.trades():
            if not trade.orderStatus:
                continue

            ib_status = self._map_ib_order_status(trade.orderStatus.status)
            if status is not None:
                status_lower = status.lower()
                if status_lower == "open" and ib_status not in (OrderStatus.PENDING, OrderStatus.SUBMITTED, OrderStatus.PARTIAL):
                    continue
                elif status_lower == "filled" and ib_status != OrderStatus.FILLED:
                    continue
                elif status_lower == "cancelled" and ib_status != OrderStatus.CANCELLED:
                    continue

            order_id = str(trade.orderStatus.orderId)
            symbol = trade.contract.symbol

            side = OrderSide.BUY if trade.order.action == "BUY" else OrderSide.SELL
            order_type = self._map_ib_order_type(trade.order.orderType)
            quantity = int(trade.order.totalQuantity)
            price = float(trade.order.lmtPrice) if trade.order.lmtPrice else None
            stop_price = float(trade.order.auxPrice) if trade.order.auxPrice else None

            order = Order(
                order_id=order_id,
                symbol=symbol,
                side=side,
                order_type=order_type,
                quantity=quantity,
                price=price,
                stop_price=stop_price,
                status=ib_status,
                filled_quantity=int(trade.orderStatus.filled),
                avg_fill_price=float(trade.orderStatus.avgFillPrice) if trade.orderStatus.avgFillPrice else None,
                commission=float(trade.commissionReport().commission) if trade.commissionReport() else None
            )

            orders.append(order)
            self._orders[order_id] = order

        return orders

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

    def _map_ib_order_type(self, order_type: str) -> OrderType:
        """Map IB order type to internal OrderType enum."""
        type_map = {
            'MKT': OrderType.MARKET,
            'LMT': OrderType.LIMIT,
            'STP': OrderType.STOP,
            'STP LMT': OrderType.STOP_LIMIT,
        }
        return type_map.get(order_type, OrderType.MARKET)

    def _setup_order_callbacks(self):
        """Setup callbacks for order status updates."""
        self.ib.orderStatusEvent += self._on_order_status
        logger.info("Order callbacks registered")

    def _on_order_status(self, trade):
        """Handle order status updates from IBKR."""
        if trade.orderStatus and trade.orderStatus.orderId:
            order_id = str(trade.orderStatus.orderId)
            ib_status = self._map_ib_order_status(trade.orderStatus.status)

            if order_id in self._orders:
                order = self._orders[order_id]
                old_status = order.status
                order.status = ib_status
                order.filled_quantity = int(trade.orderStatus.filled)
                order.avg_fill_price = float(trade.orderStatus.avgFillPrice) if trade.orderStatus.avgFillPrice else None

                if trade.commissionReport():
                    order.commission = float(trade.commissionReport().commission)

                logger.info(f"Order {order_id} status updated: {old_status} -> {ib_status}")

    def _setup_position_callbacks(self):
        """Setup callbacks for position updates."""
        self.ib.positionEvent += self._on_position_update
        logger.info("Position callbacks registered")

    def _on_position_update(self, position):
        """Handle position updates."""
        symbol = position.contract.symbol
        quantity = position.position
        logger.info(f"Position update for {symbol}: {quantity} shares")

    def _setup_account_callbacks(self):
        """Setup callbacks for account value updates."""
        self.ib.accountValueEvent += self._on_account_update
        logger.info("Account callbacks registered")

    def _on_account_update(self, value):
        """Handle account value updates."""
        tag = value.tag
        val = value.value
        try:
            self._account_values[tag] = float(val)
            logger.debug(f"Account value update: {tag} = {val}")
        except (ValueError, TypeError):
            pass

    async def get_portfolio_summary(self) -> Dict[str, Any]:
        """
        Get portfolio summary including:
        - total_value: Total portfolio value
        - cash_balance: Available cash
        - invested_value: Value of all positions
        - buying_power: Available buying power
        - margin_used: How much margin is used
        - open_positions: Number of open positions
        - daily_pnl: Today's P&L
        - total_pnl: Total realized P&L
        """
        if not self.is_connected:
            raise ConnectionError("Not connected to IBKR")

        account = await self.get_account()
        positions = await self.get_positions()

        invested_value = sum(pos.market_value for pos in positions)
        open_positions = len([pos for pos in positions if pos.quantity != 0])
        margin_used = account.portfolio_value - account.margin_available

        return {
            "total_value": account.portfolio_value,
            "cash_balance": account.cash_balance,
            "invested_value": invested_value,
            "buying_power": account.buying_power,
            "margin_used": margin_used,
            "open_positions": open_positions,
            "daily_pnl": account.daily_pnl,
            "total_pnl": account.total_pnl
        }

    async def subscribe_market_data(self, symbol: str) -> None:
        """Subscribe to real-time market data for a symbol."""
        if not self.is_connected:
            raise ConnectionError("Not connected to IBKR")

        contract = Stock(symbol, self.exchange, self.currency)
        ticker = self.ib.reqMktData(contract)
        self._tickers[symbol] = ticker
        logger.info(f"Subscribed to market data for {symbol}")

    def get_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get current quote for subscribed symbol."""
        if symbol not in self._tickers:
            logger.warning(f"No ticker data for {symbol}")
            return None

        ticker = self._tickers[symbol]
        return {
            "bid": ticker.bid,
            "ask": ticker.ask,
            "last": ticker.last,
            "volume": ticker.volume,
            "high": ticker.high,
            "low": ticker.low,
            "close": ticker.close,
            "bid_size": ticker.bidSize,
            "ask_size": ticker.askSize
        }
