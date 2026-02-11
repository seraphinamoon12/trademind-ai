"""Async broker wrapper around the threaded IBKR client.

DEPRECATED: This broker implementation is deprecated and will be removed in v2.0.
Please use IBKRInsyncBroker (ib_insync-based) instead.

To switch to the new broker, ensure ibkr_use_insync=True in your configuration.
See docs/MIGRATION_TO_IB_INSYNC.md for migration guide.
"""
import asyncio
import os
import warnings
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
import logging

from src.brokers.base import (
    BaseBroker, Order, Position, Account,
    OrderStatus, OrderType, OrderSide
)
from src.brokers.ibkr.threaded_client import IBKRClientThread, Request

try:
    from ibapi.contract import Contract
    from ibapi.order import Order as IBOrder
except ImportError:
    Contract = None
    IBOrder = None

logger = logging.getLogger(__name__)


class IBKRThreadedBroker(BaseBroker):
    """Async broker wrapper using threaded IBKR client.

    DEPRECATED: This broker is deprecated and will be removed in v2.0.
    Use IBKRInsyncBroker (ib_insync-based) for better performance and stability.
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 7497,
        client_id: int = 10,
        account: Optional[str] = None,
        paper_trading: bool = True
    ):
        warnings.warn(
            "IBKRThreadedBroker is deprecated. Use IBKRInsyncBroker instead. "
            "This class will be removed in v2.0. Set ibkr_use_insync=True to use the new broker.",
            DeprecationWarning,
            stacklevel=2
        )
        logger.warning(
            "[DEPRECATED] Using IBKRThreadedBroker. "
            "Set ibkr_use_insync=True to use IBKRInsyncBroker instead."
        )
        super().__init__()
        self.host = host
        self.port = port
        self.client_id = client_id
        self.account = account or os.getenv("IBKR_ACCOUNT", "")
        self.paper_trading = paper_trading
        self.exchange = "SMART"
        self.currency = "USD"

        self._thread: Optional[IBKRClientThread] = None
        self._next_req_id = 1000
        self._req_id_lock = asyncio.Lock()
        self._orders: Dict[str, Order] = {}

    def _get_next_req_id(self) -> int:
        """Get next request ID."""
        req_id = self._next_req_id
        self._next_req_id += 1
        return req_id

    async def _wait_for_request(self, request: Request, timeout: float = 10.0) -> Any:
        """Wait for a request to complete in the thread."""
        try:
            await asyncio.wait_for(
                asyncio.to_thread(request.event.wait),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            if self._thread and self._thread.request_manager:
                self._thread.request_manager.remove_request(request.request_id)
            raise TimeoutError(f"Request {request.action} timed out")

        if request.error:
            raise RuntimeError(request.error)

        return request.result

    async def connect(self) -> None:
        """Establish connection to IBKR TWS or Gateway."""
        if self._thread and self._thread.running.is_set():
            logger.warning("Already connected to IBKR")
            return

        logger.info(f"Connecting to IBKR at {self.host}:{self.port}...")

        self._thread = IBKRClientThread(
            self.host,
            self.port,
            self.client_id
        )

        self._thread.start()

        # Wait for connection to be established (nextValidId callback)
        try:
            for _ in range(30):  # Wait up to 3 seconds
                await asyncio.sleep(0.1)
                if self._thread.wrapper.next_order_id is not None:
                    break
            else:
                raise TimeoutError("Connection timeout - nextValidId not received")

            self._connected = True
            logger.info("Successfully connected to IBKR")
        except Exception as e:
            self._thread.stop()
            self._thread.join(timeout=2)
            self._thread = None
            self._connected = False
            logger.error(f"Failed to connect to IBKR: {e}")
            raise

    async def disconnect(self) -> None:
        """Close connection to IBKR."""
        if not self._connected:
            return

        if self._thread:
            self._thread.stop()
            self._thread.join(timeout=3)
            self._thread = None

        self._connected = False
        logger.info("Disconnected from IBKR")

    async def get_account(self) -> Account:
        """Get account information."""
        if not self.is_connected:
            raise ConnectionError("Not connected to IBKR")

        req_id = self._get_next_req_id()
        request = self._thread.get_account_summary(req_id)

        await self._wait_for_request(request, timeout=10)

        wrapper = self._thread.wrapper
        account_id = self.account or (wrapper.managed_accounts[0] if wrapper.managed_accounts else "unknown")

        # Try account_values first (from reqAccountUpdates), then account_summary (from reqAccountSummary)
        account_data = wrapper.account_values.get(account_id, {})
        if not account_data:
            account_data = wrapper.account_summary.get(account_id, {})

        def safe_float(value, default=0.0):
            try:
                return float(value) if value else default
            except (ValueError, TypeError):
                return default

        cash_balance = safe_float(account_data.get('TotalCashValue') or account_data.get('SettledCash'))
        portfolio_value = safe_float(account_data.get('NetLiquidation'))
        buying_power = safe_float(account_data.get('BuyingPower'))

        return Account(
            account_id=account_id,
            cash_balance=cash_balance,
            portfolio_value=portfolio_value,
            buying_power=buying_power,
            margin_available=safe_float(account_data.get('AvailableFunds')),
            total_pnl=safe_float(account_data.get('RealizedPnL')),
            daily_pnl=0.0,
            currency=self.currency,
            positions=await self.get_positions()
        )

    async def get_positions(self) -> List[Position]:
        """Get all current positions."""
        if not self.is_connected:
            raise ConnectionError("Not connected to IBKR")

        request = self._thread.get_positions()
        await self._wait_for_request(request, timeout=10)

        positions_data = self._thread.wrapper.positions
        positions = []

        for pos in positions_data:
            symbol = pos["symbol"]
            quantity = int(pos["position"])
            avg_cost = pos["avgCost"]

            try:
                market_price = await self.get_market_price(symbol)
            except (ValueError, ConnectionError, TimeoutError) as e:
                logger.warning(f"Could not get market price for {symbol}: {e}, using avg_cost")
                market_price = avg_cost

            market_value = abs(quantity * market_price)
            unrealized_pnl = (market_price - avg_cost) * quantity

            positions.append(Position(
                symbol=symbol,
                quantity=quantity,
                avg_cost=avg_cost,
                current_price=market_price,
                market_value=market_value,
                unrealized_pnl=unrealized_pnl
            ))

        return positions

    async def get_orders(self, status: Optional[str] = None) -> List[Order]:
        """Get orders with optional status filtering."""
        if not self.is_connected:
            raise ConnectionError("Not connected to IBKR")

        request = self._thread.get_orders()
        await self._wait_for_request(request, timeout=10)

        open_orders = self._thread.wrapper.open_orders
        orders = []

        for order_data in open_orders:
            order_id = str(order_data["orderId"])
            symbol = order_data["contract"].symbol
            ib_order = order_data["order"]

            side = OrderSide.BUY if ib_order.action == "BUY" else OrderSide.SELL
            order_type = self._map_ib_order_type(ib_order.orderType)

            order = Order(
                order_id=order_id,
                symbol=symbol,
                side=side,
                order_type=order_type,
                quantity=int(ib_order.totalQuantity),
                price=float(ib_order.lmtPrice) if ib_order.lmtPrice else None,
                stop_price=float(ib_order.auxPrice) if ib_order.auxPrice else None,
                status=self._map_ib_order_status(order_data["orderState"].status)
            )

            orders.append(order)
            self._orders[order_id] = order

        return orders

    async def place_order(self, order: Order) -> str:
        """Place an order and return order ID."""
        if not self.is_connected:
            raise ConnectionError("Not connected to IBKR")

        def _place_order():
            contract = Contract()
            contract.symbol = order.symbol
            contract.secType = "STK"
            contract.exchange = self.exchange
            contract.currency = self.currency

            ib_order = IBOrder()
            ib_order.action = order.side.value
            ib_order.totalQuantity = order.quantity
            ib_order.orderType = order.order_type.value

            if order.order_type == OrderType.LIMIT:
                ib_order.lmtPrice = order.price or 0.0
            elif order.order_type == OrderType.STOP:
                ib_order.auxPrice = order.stop_price or 0.0
            elif order.order_type == OrderType.STOP_LIMIT:
                ib_order.lmtPrice = order.price or 0.0
                ib_order.auxPrice = order.stop_price or 0.0

            order_id = self._thread.wrapper.next_order_id
            self._thread.wrapper.next_order_id += 1

            self._thread.client.placeOrder(order_id, contract, ib_order)
            return str(order_id)

        order_id = await asyncio.to_thread(_place_order)
        order.order_id = order_id
        order.status = OrderStatus.SUBMITTED
        self._orders[order_id] = order

        logger.info(f"Placed order {order_id} for {order.symbol}")
        return order_id

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order by ID."""
        if not self.is_connected:
            raise ConnectionError("Not connected to IBKR")

        try:
            await asyncio.to_thread(self._thread.client.cancelOrder, int(order_id))
            if order_id in self._orders:
                self._orders[order_id].status = OrderStatus.CANCELLED
            logger.info(f"Cancelled order {order_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            return False

    async def get_order_status(self, order_id: str) -> OrderStatus:
        """Get status of an order."""
        if order_id in self._orders:
            return self._orders[order_id].status

        ib_order_id = int(order_id)
        if ib_order_id in self._thread.wrapper.orders:
            status_str = self._thread.wrapper.orders[ib_order_id]["status"]
            return self._map_ib_order_status(status_str)

        return OrderStatus.PENDING

    async def get_market_price(self, symbol: str) -> float:
        """Get current market price for a symbol."""
        if not self.is_connected:
            raise ConnectionError("Not connected to IBKR")

        req_id = self._get_next_req_id()
        request = self._thread.get_market_price(symbol, req_id)

        await self._wait_for_request(request, timeout=5)

        # Poll for market data to arrive (with timeout)
        max_wait = 2.0
        poll_interval = 0.1
        elapsed = 0.0

        while elapsed < max_wait:
            data = self._thread.wrapper.market_data.get(req_id, {})
            price = data.get("last") or data.get("close") or data.get("bid")
            if price is not None:
                break
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        # Cancel market data subscription
        await asyncio.to_thread(self._thread.client.cancelMktData, req_id)

        data = self._thread.wrapper.market_data.get(req_id, {})
        price = data.get("last") or data.get("close") or data.get("bid")

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

    async def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get portfolio summary."""
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

    async def get_historical_bars(
        self,
        symbol: str,
        duration: str = "1 D",
        bar_size: str = "1 min",
        what_to_show: str = "TRADES",
        use_rth: bool = True,
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get historical OHLCV bars for a symbol."""
        if not self.is_connected:
            raise ConnectionError("Not connected to IBKR")

        req_id = self._get_next_req_id()
        request = self._thread.get_historical_data(
            symbol, req_id,
            duration=duration,
            bar_size=bar_size,
            what_to_show=what_to_show,
            use_rth=use_rth,
            end_date=end_date or ""
        )

        await self._wait_for_request(request, timeout=30)

        bars = self._thread.wrapper.historical_data.get(req_id, [])
        result = []

        for bar in bars:
            bar_date = bar.date
            if isinstance(bar_date, str):
                try:
                    bar_date = datetime.strptime(bar_date, "%Y%m%d %H:%M:%S")
                except ValueError:
                    try:
                        bar_date = datetime.strptime(bar_date.split()[0], "%Y%m%d")
                    except ValueError:
                        logger.warning(f"Could not parse bar date: {bar_date}")
                        continue

            result.append({
                "date": bar_date,
                "open": bar.open,
                "high": bar.high,
                "low": bar.low,
                "close": bar.close,
                "volume": bar.volume,
                "average": bar.average
            })

        return result

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

    async def subscribe_market_data(self, symbol: str) -> None:
        """Subscribe to real-time market data for a symbol."""
        pass

    def get_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get current quote for subscribed symbol."""
        pass
