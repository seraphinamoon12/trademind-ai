"""Interactive Brokers broker implementation using ibapi with thread-based wrapper."""
import asyncio
import os
import threading
import time
import queue
from typing import Optional, List, Dict, Any, Tuple, Callable
from datetime import datetime
import logging

try:
    from ibapi.client import EClient
    from ibapi.wrapper import EWrapper
    from ibapi.contract import Contract
    from ibapi.order import Order as IBOrder
    from ibapi.common import BarData
except ImportError:
    EClient = None
    EWrapper = None
    Contract = None
    IBOrder = None
    BarData = None

from src.brokers.base import (
    BaseBroker, Order, Position, Account,
    OrderStatus, OrderType, OrderSide
)

logger = logging.getLogger(__name__)


class IBKRWrapper(EWrapper):
    """Wrapper to receive IB API callbacks."""

    def __init__(self):
        super().__init__()
        self.next_order_id = None
        self.account_values = {}
        self.positions = []
        self.account_summary = {}
        self.orders = {}
        self.open_orders = []
        self.market_data = {}
        self.historical_data = {}
        self.managed_accounts = []
        self.error_messages = []

        # Synchronization events
        self.connected_event = threading.Event()
        self.next_valid_id_event = threading.Event()
        self.account_download_event = threading.Event()
        self.positions_event = threading.Event()
        self.account_summary_event = threading.Event()
        self.orders_event = threading.Event()
        self.market_data_event = threading.Event()
        self.historical_data_event = threading.Event()

    def nextValidId(self, orderId: int):
        """Callback when connection is established."""
        super().nextValidId(orderId)
        self.next_order_id = orderId
        self.next_valid_id_event.set()
        self.connected_event.set()
        logger.info(f"Connected to IB Gateway. Next valid order ID: {orderId}")

    def error(self, reqId: int, errorCode: int, errorString: str):
        """Callback for error messages."""
        super().error(reqId, errorCode, errorString)

        # Codes 2104, 2106, 2158 are informational, not errors
        if errorCode in [2104, 2106, 2158]:
            logger.info(f"IB Info [{errorCode}]: {errorString}")
            return

        logger.error(f"IB Error [{errorCode}] ReqId {reqId}: {errorString}")
        self.error_messages.append({
            "reqId": reqId,
            "errorCode": errorCode,
            "errorString": errorString,
            "timestamp": datetime.now()
        })

    def managedAccounts(self, accountsList: str):
        """Callback with list of managed accounts."""
        super().managedAccounts(accountsList)
        self.managed_accounts = accountsList.split(",")
        logger.info(f"Managed accounts: {self.managed_accounts}")

    def accountSummary(self, reqId: int, account: str, tag: str, value: str, currency: str):
        """Callback for account summary data."""
        super().accountSummary(reqId, account, tag, value, currency)
        if account not in self.account_summary:
            self.account_summary[account] = {}
        self.account_summary[account][tag] = value

    def accountSummaryEnd(self, reqId: int):
        """Callback when account summary is complete."""
        super().accountSummaryEnd(reqId)
        self.account_summary_event.set()

    def updateAccountValue(self, key: str, val: str, currency: str, accountName: str):
        """Callback for account value updates."""
        super().updateAccountValue(key, val, currency, accountName)
        if accountName not in self.account_values:
            self.account_values[accountName] = {}
        self.account_values[accountName][key] = val

    def accountDownloadEnd(self, accountName: str):
        """Callback when account download is complete."""
        super().accountDownloadEnd(accountName)
        self.account_download_event.set()
        logger.info(f"Account download complete for {accountName}")

    def position(self, account: str, contract: Contract, position: float, avgCost: float):
        """Callback for position data."""
        super().position(account, contract, position, avgCost)
        self.positions.append({
            "account": account,
            "symbol": contract.symbol,
            "position": position,
            "avgCost": avgCost,
            "contract": contract
        })

    def positionEnd(self):
        """Callback when all positions have been received."""
        super().positionEnd()
        self.positions_event.set()
        logger.info(f"Received {len(self.positions)} positions")

    def openOrder(self, orderId: int, contract: Contract, order: IBOrder, orderState):
        """Callback for open order data."""
        super().openOrder(orderId, contract, order, orderState)
        self.open_orders.append({
            "orderId": orderId,
            "contract": contract,
            "order": order,
            "orderState": orderState
        })

    def openOrderEnd(self):
        """Callback when all open orders have been received."""
        super().openOrderEnd()
        self.orders_event.set()
        logger.info(f"Received {len(self.open_orders)} open orders")

    def orderStatus(self, orderId: int, status: str, filled: float, remaining: float,
                    avgFillPrice: float, permId: int, parentId: int, lastFillPrice: float,
                    clientId: int, whyHeld: str, mktCapPrice: float):
        """Callback for order status updates."""
        super().orderStatus(orderId, status, filled, remaining, avgFillPrice, permId,
                           parentId, lastFillPrice, clientId, whyHeld, mktCapPrice)
        self.orders[orderId] = {
            "status": status,
            "filled": filled,
            "remaining": remaining,
            "avgFillPrice": avgFillPrice
        }
        logger.info(f"Order {orderId} status: {status}, filled: {filled}")

    def tickPrice(self, reqId: int, tickType: int, price: float, attrib):
        """Callback for market data price tick."""
        super().tickPrice(reqId, tickType, price, attrib)
        if reqId not in self.market_data:
            self.market_data[reqId] = {}

        # tickType: 1=bid, 2=ask, 4=last, 6=high, 7=low, 9=close
        tick_map = {1: "bid", 2: "ask", 4: "last", 6: "high", 7: "low", 9: "close"}
        if tickType in tick_map:
            self.market_data[reqId][tick_map[tickType]] = price

    def tickSize(self, reqId: int, tickType: int, size: int):
        """Callback for market data size tick."""
        super().tickSize(reqId, tickType, size)
        if reqId not in self.market_data:
            self.market_data[reqId] = {}

        # tickType: 0=bidSize, 3=askSize, 5=lastSize, 8=volume
        tick_map = {0: "bidSize", 3: "askSize", 5: "lastSize", 8: "volume"}
        if tickType in tick_map:
            self.market_data[reqId][tick_map[tickType]] = size

    def historicalData(self, reqId: int, bar: BarData):
        """Callback for historical data bars."""
        super().historicalData(reqId, bar)
        if reqId not in self.historical_data:
            self.historical_data[reqId] = []
        self.historical_data[reqId].append(bar)

    def historicalDataEnd(self, reqId: int, start: str, end: str):
        """Callback when historical data is complete."""
        super().historicalDataEnd(reqId, start, end)
        self.historical_data_event.set()
        logger.info(f"Historical data complete for reqId {reqId}")


class IBKRClient(EClient):
    """EClient implementation that runs in separate thread."""

    def __init__(self, wrapper):
        super().__init__(wrapper)


class IBKRBroker(BaseBroker):
    """Interactive Brokers broker implementation using ibapi."""

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
        self.account = account or os.getenv("IBKR_ACCOUNT", "")
        self.paper_trading = paper_trading
        self.exchange = "SMART"
        self.currency = "USD"

        if EClient is None or EWrapper is None:
            raise ImportError(
                "ibapi is not installed. Please install it with: pip install ibapi"
            )

        # Create wrapper and client
        self.wrapper = IBKRWrapper()
        self.client = IBKRClient(self.wrapper)

        # Thread management
        self.api_thread = None
        self._req_id = 1000
        self._req_id_lock = threading.Lock()

        self._orders: Dict[str, Order] = {}

    def _get_next_req_id(self) -> int:
        """Get next request ID in thread-safe manner."""
        with self._req_id_lock:
            req_id = self._req_id
            self._req_id += 1
            return req_id

    def _run_client(self):
        """Run the client in a separate thread."""
        try:
            self.client.run()
        except Exception as e:
            logger.error(f"Client thread error: {e}")

    async def connect(self) -> None:
        """Establish connection to IBKR TWS or Gateway."""
        try:
            # Connect in thread-safe manner
            def _connect():
                self.client.connect(self.host, self.port, self.client_id)
                return True

            result = await asyncio.to_thread(_connect)

            # Start API thread
            self.api_thread = threading.Thread(target=self._run_client, daemon=True)
            self.api_thread.start()

            # Wait for connection with timeout
            if not self.wrapper.connected_event.wait(timeout=10):
                raise TimeoutError("Connection timeout")

            if not self.wrapper.next_valid_id_event.wait(timeout=10):
                raise TimeoutError("Next valid ID timeout")

            self._connected = True

            # Get account information
            managed_accounts = self.wrapper.managed_accounts
            account_id = self.account or os.getenv("IBKR_ACCOUNT") or (managed_accounts[0] if managed_accounts else None)

            if account_id:
                self.account = account_id
                # Request account updates
                await asyncio.to_thread(self.client.reqAccountUpdates, True, account_id)
                # Request account summary
                await asyncio.to_thread(self.client.reqAccountSummary, 9001, "All", "$LEDGER")
                await asyncio.to_thread(lambda: self.wrapper.account_summary_event.wait(timeout=5))
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
            await asyncio.to_thread(self.client.disconnect)
            if self.api_thread and self.api_thread.is_alive():
                self.api_thread.join(timeout=2)
            self._connected = False
            logger.info("Disconnected from IBKR")

    async def place_order(self, order: Order) -> str:
        """Place an order and return order ID."""
        if not self.is_connected:
            raise ConnectionError("Not connected to IBKR")

        def _place_order():
            # Create contract
            contract = Contract()
            contract.symbol = order.symbol
            contract.secType = "STK"
            contract.exchange = self.exchange
            contract.currency = self.currency

            # Create IB order
            ib_order = IBOrder()
            ib_order.action = order.side.value
            ib_order.totalQuantity = order.quantity
            ib_order.orderType = order.order_type.value

            if order.order_type == OrderType.LIMIT:
                ib_order.lmtPrice = order.price
            elif order.order_type == OrderType.STOP:
                ib_order.auxPrice = order.stop_price
            elif order.order_type == OrderType.STOP_LIMIT:
                ib_order.lmtPrice = order.price
                ib_order.auxPrice = order.stop_price

            # Place order
            order_id = self.wrapper.next_order_id
            self.wrapper.next_order_id += 1

            self.client.placeOrder(order_id, contract, ib_order)

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
            await asyncio.to_thread(self.client.cancelOrder, int(order_id), "")
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
        if ib_order_id in self.wrapper.orders:
            status_str = self.wrapper.orders[ib_order_id]["status"]
            return self._map_ib_order_status(status_str)

        logger.warning(f"Order {order_id} not found")
        return OrderStatus.PENDING

    async def get_orders(self, status: Optional[str] = None) -> List[Order]:
        """Get orders with optional status filtering."""
        if not self.is_connected:
            raise ConnectionError("Not connected to IBKR")

        def _get_orders():
            self.wrapper.open_orders.clear()
            self.wrapper.orders_event.clear()
            self.client.reqAllOpenOrders()
            self.wrapper.orders_event.wait(timeout=5)
            return self.wrapper.open_orders

        open_orders = await asyncio.to_thread(_get_orders)

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

    async def get_positions(self) -> List[Position]:
        """Get all current positions."""
        if not self.is_connected:
            raise ConnectionError("Not connected to IBKR")

        def _get_positions():
            self.wrapper.positions.clear()
            self.wrapper.positions_event.clear()
            self.client.reqPositions()
            self.wrapper.positions_event.wait(timeout=5)
            return self.wrapper.positions

        positions_data = await asyncio.to_thread(_get_positions)

        positions = []
        for pos in positions_data:
            symbol = pos["symbol"]
            quantity = int(pos["position"])
            avg_cost = pos["avgCost"]

            # Get current market price
            try:
                market_price = await self.get_market_price(symbol)
            except:
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

    async def get_account(self) -> Account:
        """Get account information."""
        if not self.is_connected:
            raise ConnectionError("Not connected to IBKR")

        def _get_account_summary():
            # Request fresh account summary with ALL tags
            self.wrapper.account_summary_event.clear()
            self.wrapper.account_summary.clear()
            self.client.reqAccountSummary(9001, "All", "AccountType,NetLiquidation,TotalCashValue,SettledCash,AccruedCash,BuyingPower,EquityWithLoanValue,PreviousEquityWithLoanValue,GrossPositionValue,RegTEquity,RegTMargin,SMA,InitMarginReq,MaintMarginReq,AvailableFunds,ExcessLiquidity,Cushion,FullInitMarginReq,FullMaintMarginReq,FullAvailableFunds,FullExcessLiquidity,LookAheadNextChange,LookAheadInitMarginReq,LookAheadMaintMarginReq,LookAheadAvailableFunds,LookAheadExcessLiquidity,HighestSeverity,DayTradesRemaining,Leverage")
            self.wrapper.account_summary_event.wait(timeout=10)
            return self.wrapper.account_summary

        account_summary = await asyncio.to_thread(_get_account_summary)

        account_id = self.account or (self.wrapper.managed_accounts[0] if self.wrapper.managed_accounts else "unknown")
        account_data = account_summary.get(account_id, {})

        def safe_float(value, default=0.0):
            try:
                return float(value) if value else default
            except (ValueError, TypeError):
                return default

        # Try multiple fields for cash balance
        cash_balance = safe_float(account_data.get('TotalCashValue') or account_data.get('SettledCash') or account_data.get('AccruedCash'))
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

    async def get_market_price(self, symbol: str) -> float:
        """Get current market price for a symbol."""
        if not self.is_connected:
            raise ConnectionError("Not connected to IBKR")

        def _get_market_price():
            contract = Contract()
            contract.symbol = symbol
            contract.secType = "STK"
            contract.exchange = self.exchange
            contract.currency = self.currency

            req_id = self._get_next_req_id()
            self.wrapper.market_data[req_id] = {}
            self.wrapper.market_data_event.clear()

            self.client.reqMktData(req_id, contract, "", False, False, [])

            # Wait for data
            time.sleep(1)

            self.client.cancelMktData(req_id)

            data = self.wrapper.market_data.get(req_id, {})
            price = data.get("last") or data.get("close") or data.get("bid")

            if price is None:
                raise ValueError(f"Unable to get market price for {symbol}")

            return float(price)

        return await asyncio.to_thread(_get_market_price)

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

    async def subscribe_market_data(self, symbol: str) -> None:
        """Subscribe to real-time market data for a symbol."""
        if not self.is_connected:
            raise ConnectionError("Not connected to IBKR")

        def _subscribe():
            contract = Contract()
            contract.symbol = symbol
            contract.secType = "STK"
            contract.exchange = self.exchange
            contract.currency = self.currency

            req_id = self._get_next_req_id()
            self.client.reqMktData(req_id, contract, "", False, False, [])
            return req_id

        await asyncio.to_thread(_subscribe)
        logger.info(f"Subscribed to market data for {symbol}")

    def get_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get current quote for subscribed symbol."""
        # Find the request ID for this symbol
        for req_id, data in self.wrapper.market_data.items():
            if data:
                return {
                    "bid": data.get("bid"),
                    "ask": data.get("ask"),
                    "last": data.get("last"),
                    "volume": data.get("volume"),
                    "high": data.get("high"),
                    "low": data.get("low"),
                    "close": data.get("close"),
                    "bid_size": data.get("bidSize"),
                    "ask_size": data.get("askSize")
                }
        return None

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

        def _get_historical_data():
            contract = Contract()
            contract.symbol = symbol
            contract.secType = "STK"
            contract.exchange = self.exchange
            contract.currency = self.currency

            req_id = self._get_next_req_id()
            self.wrapper.historical_data[req_id] = []
            self.wrapper.historical_data_event.clear()

            self.client.reqHistoricalData(
                req_id,
                contract,
                end_date or "",
                duration,
                bar_size,
                what_to_show,
                1 if use_rth else 0,
                1,
                False,
                []
            )

            self.wrapper.historical_data_event.wait(timeout=30)
            return self.wrapper.historical_data.get(req_id, [])

        bars = await asyncio.to_thread(_get_historical_data)

        result = []
        for bar in bars:
            bar_date = bar.date
            if isinstance(bar_date, str):
                try:
                    bar_date = datetime.strptime(bar_date, "%Y%m%d %H:%M:%S")
                except ValueError:
                    try:
                        bar_date = datetime.strptime(bar_date.split()[0], "%Y%m%d")
                    except:
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
