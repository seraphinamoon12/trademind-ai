"""IBKR broker implementation using ib_insync library."""
import asyncio
import logging
import time
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
from enum import Enum

from ib_insync import IB, Stock, MarketOrder, LimitOrder, StopOrder, Order, Contract
from ib_insync.wrapper import RequestError

from src.brokers.base import (
    BaseBroker,
    Position,
    Account,
    Order as BaseOrder,
    OrderStatus,
    OrderType,
    OrderSide
)
from src.config import settings

logger = logging.getLogger(__name__)

# Constants for operations (magic numbers extracted to constants)
DEFAULT_POSITIONS_WAIT_TIME = 0.5
DEFAULT_POST_CONNECT_WAIT_TIME = 1.0
DEFAULT_MARKET_PRICE_WAIT_TIME = 1.0
DEFAULT_RECONNECT_EXPONENTIAL_LIMIT = 5


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class IBKRInsyncBroker(BaseBroker):
    """IBKR broker implementation using ib_insync (async)."""

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        client_id: Optional[int] = None,
        account: Optional[str] = None
    ):
        super().__init__()
        # Fix: Don't create IB instance in __init__ to avoid event loop issues
        # Wait until connect() is called from within the running event loop
        self._ib: Optional[IB] = None
        self._host = host or settings.ibkr_host
        self._port = port or settings.ibkr_port
        self._client_id = client_id or settings.ibkr_client_id
        self._account = account or settings.ibkr_account

        self._connection_lock = asyncio.Lock()
        self._lazy_connect = settings.ibkr_insync_lazy_connect
        # Use settings for reconnection parameters instead of hardcoded values
        self._reconnect_enabled = settings.ibkr_insync_reconnect_enabled
        self._max_reconnect_attempts = settings.ibkr_insync_max_reconnect_attempts
        self._reconnect_backoff = settings.ibkr_insync_reconnect_backoff
        self._connect_timeout = settings.ibkr_insync_connect_timeout

        # Circuit breaker for reconnection failures
        self._circuit_breaker_enabled = settings.ibkr_circuit_breaker_enabled
        self._circuit_breaker_failure_threshold = settings.ibkr_circuit_breaker_failure_threshold
        self._circuit_breaker_cooldown_seconds = settings.ibkr_circuit_breaker_cooldown_seconds
        self._circuit_state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None

        # Metrics collection
        self._metrics: Dict[str, Any] = {
            'connections': 0,
            'reconnections': 0,
            'failures': 0,
            'orders_placed': 0,
            'orders_successful': 0,
            'avg_connect_time_ms': 0.0,
            'last_connect_time': None
        }

        logger.info(
            f"IBKRInsyncBroker initialized: host={self._host}, "
            f"port={self._port}, client_id={self._client_id}, "
            f"lazy_connect={self._lazy_connect}, circuit_breaker={self._circuit_breaker_enabled}"
        )

    def _get_ib(self) -> IB:
        """Get or create IB instance - ensures it's created in the correct event loop."""
        if self._ib is None:
            self._ib = IB()
        return self._ib

    async def connect(self) -> None:
        """Establish connection to IB Gateway."""
        async with self._connection_lock:
            if self._connected:
                logger.info("Already connected to IB Gateway")
                return

            if not self._check_circuit_breaker():
                raise ConnectionError("Circuit breaker is OPEN - rejecting connection attempt")

            logger.info(f"Connecting to IB Gateway at {self._host}:{self._port}")
            start_time = time.time()
            try:
                await self._get_ib().connectAsync(
                    host=self._host,
                    port=self._port,
                    clientId=self._client_id,
                    timeout=self._connect_timeout
                )

                await asyncio.sleep(DEFAULT_POST_CONNECT_WAIT_TIME)

                if not self._get_ib().isConnected():
                    logger.error("Connection failed - IB Gateway not connected after connectAsync")
                    self._record_connection_failure()
                    raise ConnectionError("Failed to connect to IB Gateway")

                self._connected = True
                self._reset_circuit_breaker()

                # Update metrics
                self._metrics['connections'] += 1
                self._metrics['last_connect_time'] = datetime.now(timezone.utc).isoformat()
                connect_time_ms = (time.time() - start_time) * 1000
                if self._metrics['connections'] == 1:
                    self._metrics['avg_connect_time_ms'] = connect_time_ms
                else:
                    self._metrics['avg_connect_time_ms'] = (
                        (self._metrics['avg_connect_time_ms'] * (self._metrics['connections'] - 1) + connect_time_ms)
                        / self._metrics['connections']
                    )

                if self._account:
                    logger.info(f"Connected to IB Gateway, account: {self._account}")
                else:
                    logger.info("Connected to IB Gateway")

                logger.info(f"Connection successful - client_id: {self._client_id}")

            except ConnectionError as e:
                logger.error(f"Connection error: {e}")
                self._record_connection_failure()
                raise
            except asyncio.TimeoutError:
                logger.error(f"Connection timeout after {self._connect_timeout}s")
                self._record_connection_failure()
                raise ConnectionError(f"Connection timeout: IB Gateway not responding")
            except Exception as e:
                logger.error(f"Unexpected connection error: {type(e).__name__}: {e}")
                self._record_connection_failure()
                raise ConnectionError(f"Could not connect to IB Gateway: {e}")

    async def disconnect(self) -> None:
        """Close connection to IB Gateway."""
        async with self._connection_lock:
            if not self._connected:
                logger.info("Not connected to IB Gateway")
                return

            logger.info("Disconnecting from IB Gateway")
            try:
                self._get_ib().disconnect()
                self._connected = False
                logger.info("Disconnected from IB Gateway")
            except Exception as e:
                logger.error(f"Error disconnecting from IB Gateway: {e}")
                raise

    async def get_positions(self) -> List[Position]:
        """Get all current positions."""
        await self._ensure_connected()

        logger.info("Fetching positions from IB Gateway")
        try:
            self._get_ib().reqPositions()

            await asyncio.sleep(DEFAULT_POSITIONS_WAIT_TIME)

            positions = []
            for pos in self._get_ib().positions():
                symbol = pos.contract.symbol
                quantity = int(pos.position)
                avg_cost = float(pos.avgCost)

                current_price = 0.0
                market_value = 0.0
                unrealized_pnl = 0.0

                positions.append(Position(
                    symbol=symbol,
                    quantity=quantity,
                    avg_cost=avg_cost,
                    current_price=current_price,
                    market_value=market_value,
                    unrealized_pnl=unrealized_pnl,
                    currency=pos.contract.currency or "USD"
                ))

            logger.info(f"Fetched {len(positions)} positions")
            return positions

        except Exception as e:
            logger.error(f"Error fetching positions: {e}")
            raise

    async def get_account(self) -> Account:
        """Get account information."""
        await self._ensure_connected()

        logger.info("Fetching account summary from IB Gateway")
        try:
            # Safely get account code with bounds checking to prevent IndexError
            account_code = self._account
            if not account_code:
                managed_accounts = self._get_ib().managedAccounts()
                if managed_accounts:
                    account_code = managed_accounts[0]

            if not account_code:
                raise ValueError("No account code available")

            summary = await self._get_ib().accountSummaryAsync()

            account_data = {}
            for item in summary:
                tag = item.tag
                value = item.value
                if tag == "AccountCode":
                    account_data["account_id"] = value
                elif tag == "TotalCashBalance":
                    account_data["cash_balance"] = float(value)
                elif tag == "NetLiquidation":
                    account_data["portfolio_value"] = float(value)
                elif tag == "BuyingPower":
                    account_data["buying_power"] = float(value)
                elif tag == "AvailableFunds":
                    account_data["margin_available"] = float(value)
                elif tag == "RealizedPnL":
                    account_data["realized_pnl"] = float(value)
                elif tag == "UnrealizedPnL":
                    account_data["unrealized_pnl"] = float(value)

            account = Account(
                account_id=account_data.get("account_id", account_code),
                cash_balance=account_data.get("cash_balance", 0.0),
                portfolio_value=account_data.get("portfolio_value", 0.0),
                buying_power=account_data.get("buying_power", 0.0),
                margin_available=account_data.get("margin_available", 0.0),
                total_pnl=account_data.get("unrealized_pnl", 0.0) + account_data.get("realized_pnl", 0.0),
                daily_pnl=0.0,
                currency="USD",
                positions=[]
            )

            logger.info(f"Fetched account: {account.account_id}")
            return account

        except Exception as e:
            logger.error(f"Error fetching account: {e}")
            raise

    async def place_order(self, order: BaseOrder) -> str:
        """Place an order and return order ID."""
        await self._ensure_connected()

        logger.info(f"Placing order: {order.side.value} {order.quantity} {order.symbol}")

        try:
            contract = Stock(
                symbol=order.symbol,
                exchange="SMART",
                currency="USD"
            )

            ib_order = Order()
            ib_order.totalQuantity = order.quantity
            ib_order.action = order.side.value

            if order.order_type == OrderType.MARKET:
                ib_order.orderType = "MKT"
            elif order.order_type == OrderType.LIMIT and order.price:
                ib_order.orderType = "LMT"
                ib_order.lmtPrice = order.price
            elif order.order_type == OrderType.STOP and order.stop_price:
                ib_order.orderType = "STP"
                ib_order.auxPrice = order.stop_price
            elif order.order_type == OrderType.STOP_LIMIT:
                if not order.stop_price:
                    raise ValueError("Stop price is required for STOP_LIMIT orders")
                if not order.price:
                    raise ValueError("Limit price is required for STOP_LIMIT orders")
                ib_order.orderType = "STP LMT"
                ib_order.auxPrice = order.stop_price
                ib_order.lmtPrice = order.price
            else:
                raise ValueError(f"Unsupported order type: {order.order_type}")

            trade = self._get_ib().placeOrder(contract, ib_order)
            order_id = str(trade.order.orderId)

            # Update metrics
            self._metrics['orders_placed'] += 1
            self._metrics['orders_successful'] += 1

            logger.info(f"Order placed: {order_id}")
            return order_id

        except Exception as e:
            # Update metrics for failed order
            self._metrics['orders_placed'] += 1
            logger.error(f"Error placing order: {e}")
            raise

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order by ID."""
        await self._ensure_connected()

        logger.info(f"Cancelling order: {order_id}")
        try:
            for trade in self._get_ib().openTrades():
                if trade.order.orderId == int(order_id):
                    self._get_ib().cancelOrder(trade.order)
                    logger.info(f"Order cancelled: {order_id}")
                    return True

            logger.warning(f"Order {order_id} not found in open trades")
            return False
        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            return False

    async def get_order_status(self, order_id: str) -> OrderStatus:
        """Get status of an order."""
        await self._ensure_connected()

        try:
            for trade in self._get_ib().openTrades():
                if trade.order.orderId == int(order_id):
                    status = trade.orderStatus.status
                    status_map = {
                        "PendingSubmit": OrderStatus.PENDING,
                        "PendingCancel": OrderStatus.PENDING,
                        "PreSubmitted": OrderStatus.PENDING,
                        "Submitted": OrderStatus.SUBMITTED,
                        "ApiCancelled": OrderStatus.CANCELLED,
                        "Cancelled": OrderStatus.CANCELLED,
                        "Filled": OrderStatus.FILLED,
                        "PartiallyFilled": OrderStatus.PARTIAL,
                        "Rejected": OrderStatus.REJECTED
                    }
                    return status_map.get(status, OrderStatus.PENDING)

            return OrderStatus.CANCELLED
        except Exception as e:
            logger.error(f"Error getting order status: {e}")
            raise

    async def get_orders(self, status: Optional[str] = None) -> List[BaseOrder]:
        """Get orders with optional status filtering."""
        await self._ensure_connected()

        logger.info(f"Fetching orders (status filter: {status})")
        try:
            orders = []
            open_trades = self._get_ib().openTrades()

            for trade in open_trades:
                ib_order = trade.order
                ib_order_status = trade.orderStatus

                order_type = OrderType.MARKET
                if ib_order.orderType == "LMT":
                    order_type = OrderType.LIMIT
                elif ib_order.orderType == "STP":
                    order_type = OrderType.STOP
                elif ib_order.orderType == "STP LMT":
                    order_type = OrderType.STOP_LIMIT

                side = OrderSide.BUY if ib_order.action == "BUY" else OrderSide.SELL

                status_map = {
                    "PendingSubmit": OrderStatus.PENDING,
                    "PendingCancel": OrderStatus.PENDING,
                    "PreSubmitted": OrderStatus.PENDING,
                    "Submitted": OrderStatus.SUBMITTED,
                    "ApiCancelled": OrderStatus.CANCELLED,
                    "Cancelled": OrderStatus.CANCELLED,
                    "Filled": OrderStatus.FILLED,
                    "PartiallyFilled": OrderStatus.PARTIAL,
                    "Rejected": OrderStatus.REJECTED
                }

                order_status = status_map.get(ib_order_status.status, OrderStatus.PENDING)

                if status and order_status.value != status:
                    continue

                order = BaseOrder(
                    order_id=str(ib_order.orderId),
                    symbol=trade.contract.symbol,
                    side=side,
                    order_type=order_type,
                    quantity=int(ib_order.totalQuantity),
                    price=ib_order.lmtPrice if hasattr(ib_order, 'lmtPrice') and ib_order.lmtPrice else None,
                    stop_price=ib_order.auxPrice if hasattr(ib_order, 'auxPrice') and ib_order.auxPrice else None,
                    status=order_status,
                    filled_quantity=int(ib_order_status.filled),
                    avg_fill_price=ib_order_status.avgFillPrice if ib_order_status.avgFillPrice else None,
                    metadata={}
                )

                orders.append(order)

            logger.info(f"Fetched {len(orders)} orders")
            return orders

        except Exception as e:
            logger.error(f"Error fetching orders: {e}")
            raise

    async def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get comprehensive portfolio summary."""
        await self._ensure_connected()

        logger.info("Fetching portfolio summary")
        try:
            account = await self.get_account()
            positions = await self.get_positions()

            total_market_value = sum(pos.market_value for pos in positions)
            total_unrealized_pnl = sum(pos.unrealized_pnl for pos in positions)

            return {
                "account_id": account.account_id,
                "cash_balance": account.cash_balance,
                "portfolio_value": account.portfolio_value,
                "buying_power": account.buying_power,
                "margin_available": account.margin_available,
                "total_pnl": account.total_pnl,
                "daily_pnl": account.daily_pnl,
                "num_positions": len(positions),
                "total_market_value": total_market_value,
                "total_unrealized_pnl": total_unrealized_pnl,
                "positions": [pos.__dict__ for pos in positions],
                "currency": account.currency
            }
        except Exception as e:
            logger.error(f"Error fetching portfolio summary: {e}")
            raise

    async def get_market_price(self, symbol: str) -> float:
        """Get current market price for a symbol."""
        await self._ensure_connected()

        logger.info(f"Fetching market price for {symbol}")
        try:
            contract = Stock(
                symbol=symbol,
                exchange="SMART",
                currency="USD"
            )

            ticker = self._get_ib().reqMktData(contract, "", False, False)

            await asyncio.sleep(DEFAULT_MARKET_PRICE_WAIT_TIME)

            price = ticker.marketPrice()
            if price == 0:
                price = ticker.last or ticker.ask or ticker.bid or 0.0

            logger.info(f"Market price for {symbol}: {price}")
            return price

        except Exception as e:
            logger.error(f"Error fetching market price: {e}")
            raise

    async def validate_order(self, order: BaseOrder) -> Tuple[bool, str]:
        """Validate if an order can be placed."""
        await self._ensure_connected()

        if not order.symbol:
            return False, "Symbol is required"

        if order.quantity <= 0:
            return False, "Quantity must be positive"

        if order.order_type == OrderType.LIMIT and not order.price:
            return False, "Limit price is required for limit orders"

        if order.order_type == OrderType.STOP and not order.stop_price:
            return False, "Stop price is required for stop orders"

        if order.order_type == OrderType.STOP_LIMIT:
            if not order.stop_price:
                return False, "Stop price is required for stop-limit orders"
            if order.stop_price <= 0:
                return False, "Stop price must be positive for stop-limit orders"
            if not order.price:
                return False, "Limit price is required for stop-limit orders"
            if order.price <= 0:
                return False, "Limit price must be positive for stop-limit orders"

        try:
            price = await self.get_market_price(order.symbol)
            if price <= 0:
                return False, "Cannot get market price"

            account = await self.get_account()
            order_value = order.quantity * price

            if order_value > account.buying_power:
                return False, f"Insufficient buying power: need ${order_value:.2f}, have ${account.buying_power:.2f}"

        except Exception as e:
            return False, f"Validation error: {e}"

        return True, "Order is valid"

    async def get_historical_bars(
        self,
        symbol: str,
        duration: str,
        bar_size: str,
        what_to_show: str = "TRADES",
        use_rth: bool = True,
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get historical OHLCV bars."""
        await self._ensure_connected()

        logger.info(f"Fetching historical bars for {symbol}: {duration}, {bar_size}")
        try:
            contract = Stock(
                symbol=symbol,
                exchange="SMART",
                currency="USD"
            )

            bars = await self._get_ib().reqHistoricalDataAsync(
                contract,
                endDateTime=end_date or "",
                durationStr=duration,
                barSizeSetting=bar_size,
                whatToShow=what_to_show,
                useRTH=use_rth,
                formatDate=1
            )

            result = []
            for bar in bars:
                result.append({
                    "date": bar.date.isoformat() if bar.date else None,
                    "open": float(bar.open) if bar.open else None,
                    "high": float(bar.high) if bar.high else None,
                    "low": float(bar.low) if bar.low else None,
                    "close": float(bar.close) if bar.close else None,
                    "volume": int(bar.volume) if bar.volume else None,
                    "count": int(bar.barCount) if hasattr(bar, 'barCount') and bar.barCount else None
                })

            logger.info(f"Fetched {len(result)} historical bars")
            return result

        except Exception as e:
            logger.error(f"Error fetching historical bars: {e}")
            raise

    async def _ensure_connected(self) -> None:
        """Ensure connection to IB Gateway, reconnect if needed."""
        if not self._connected:
            if self._lazy_connect:
                logger.info("Not connected, lazy connect enabled - attempting to connect")
                await self.connect()
            else:
                raise ConnectionError("Not connected to IB Gateway")
        elif not self._get_ib().isConnected():
            logger.warning("Connection lost, attempting to reconnect")
            await self._reconnect()

    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics for monitoring.

        Returns:
            Dictionary of current metrics including connection stats,
            reconnection counts, failure counts, and order statistics.
        """
        return self._metrics.copy()

    def _check_circuit_breaker(self) -> bool:
        """Check if connection attempt is allowed based on circuit breaker state.

        Returns:
            True if connection is allowed, False if circuit breaker is OPEN.
        """
        if not self._circuit_breaker_enabled:
            return True

        now = time.monotonic()

        if self._circuit_state == CircuitState.CLOSED:
            return True
        elif self._circuit_state == CircuitState.OPEN:
            if self._last_failure_time and (now - self._last_failure_time) >= self._circuit_breaker_cooldown_seconds:
                logger.info("Circuit breaker cooldown elapsed, transitioning to HALF_OPEN")
                self._circuit_state = CircuitState.HALF_OPEN
                return True
            else:
                remaining = int(self._circuit_breaker_cooldown_seconds - (now - self._last_failure_time)) if self._last_failure_time else 0
                logger.warning(f"Circuit breaker OPEN - rejecting connection (cooldown: {remaining}s remaining)")
                return False
        elif self._circuit_state == CircuitState.HALF_OPEN:
            logger.info("Circuit breaker HALF_OPEN - allowing test connection")
            return True
        return True

    def _record_connection_failure(self) -> None:
        """Record a connection failure and update circuit breaker state."""
        if not self._circuit_breaker_enabled:
            return

        self._failure_count += 1
        self._last_failure_time = time.monotonic()

        # Update metrics
        self._metrics['failures'] += 1

        logger.warning(
            f"Connection failure #{self._failure_count} recorded "
            f"(threshold: {self._circuit_breaker_failure_threshold})"
        )

        if self._circuit_state == CircuitState.HALF_OPEN:
            logger.error("Circuit breaker: HALF_OPEN connection failed, returning to OPEN")
            self._circuit_state = CircuitState.OPEN
        elif self._failure_count >= self._circuit_breaker_failure_threshold:
            logger.error(
                f"Circuit breaker: {self._failure_count} failures reached, "
                f"opening circuit (cooldown: {self._circuit_breaker_cooldown_seconds}s)"
            )
            self._circuit_state = CircuitState.OPEN

    def _reset_circuit_breaker(self) -> None:
        """Reset circuit breaker after successful connection."""
        if not self._circuit_breaker_enabled:
            return

        if self._circuit_state != CircuitState.CLOSED:
            logger.info(
                f"Circuit breaker: Connection successful, "
                f"resetting from {self._circuit_state.value} to CLOSED "
                f"(failures: {self._failure_count})"
            )
        self._circuit_state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = None

    async def _reconnect(self) -> None:
        """Attempt to reconnect to IB Gateway."""
        if not self._reconnect_enabled:
            logger.warning("Reconnection disabled")
            return

        if not self._check_circuit_breaker():
            raise ConnectionError("Circuit breaker is OPEN - rejecting reconnection attempt")

        logger.info("Starting reconnection sequence...")
        for attempt in range(self._max_reconnect_attempts):
            backoff = self._reconnect_backoff * (2 ** min(attempt, DEFAULT_RECONNECT_EXPONENTIAL_LIMIT))
            logger.info(f"Reconnect attempt {attempt + 1}/{self._max_reconnect_attempts} in {backoff}s")

            await asyncio.sleep(backoff)

            try:
                await self._get_ib().connectAsync(
                    host=self._host,
                    port=self._port,
                    clientId=self._client_id,
                    timeout=self._connect_timeout
                )

                await asyncio.sleep(DEFAULT_POST_CONNECT_WAIT_TIME)

                if self._get_ib().isConnected():
                    self._connected = True
                    self._reset_circuit_breaker()
                    # Update metrics
                    self._metrics['reconnections'] += 1
                    logger.info(f"Successfully reconnected to IB Gateway (attempt {attempt + 1})")
                    return
                else:
                    logger.warning(f"Reconnect attempt {attempt + 1}: connectAsync succeeded but IB not connected")
                    self._record_connection_failure()

            except ConnectionError as e:
                logger.error(f"Reconnect attempt {attempt + 1} failed with connection error: {e}")
                self._record_connection_failure()
            except asyncio.TimeoutError:
                logger.error(f"Reconnect attempt {attempt + 1} failed with timeout")
                self._record_connection_failure()
            except Exception as e:
                logger.error(f"Reconnect attempt {attempt + 1} failed: {type(e).__name__}: {e}")
                self._record_connection_failure()

        logger.error(f"Failed to reconnect after {self._max_reconnect_attempts} attempts")
        raise ConnectionError(f"Unable to reconnect to IB Gateway after {self._max_reconnect_attempts} attempts")
