"""Thread-based IBKR client implementation with proper async integration."""
import asyncio
import threading
import queue
from typing import Optional, Dict, Any
import logging
from dataclasses import dataclass, field

try:
    from ibapi.client import EClient
    from ibapi.wrapper import EWrapper
    from ibapi.contract import Contract
except ImportError:
    EClient = None
    EWrapper = None
    Contract = None

logger = logging.getLogger(__name__)


@dataclass
class Request:
    """Request from main thread to IB client thread."""
    request_id: int
    action: str
    data: Dict[str, Any] = field(default_factory=dict)
    event: Optional[threading.Event] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    completed: bool = False


class IBKRWrapper(EWrapper):
    """Wrapper to receive IB API callbacks in client thread."""

    def __init__(self) -> None:
        super().__init__()
        logger.debug("IBKRWrapper.__init__()")
        self.next_order_id = None
        self.account_values: Dict[str, Dict[str, str]] = {}
        self.positions: list = []
        self.account_summary: Dict[str, Dict[str, str]] = {}
        self.orders: Dict[int, Dict[str, Any]] = {}
        self.open_orders: list = []
        self.market_data: Dict[int, Dict[str, Any]] = {}
        self.historical_data: Dict[int, list] = {}
        self.managed_accounts: list = []
        self.error_messages: list = []
        self._request_manager = None
        logger.debug("IBKRWrapper.__init__() completed")

    def set_request_manager(self, manager: "RequestManager") -> None:
        """Set reference to request manager for callback coordination."""
        self._request_manager = manager

    def nextValidId(self, orderId: int):
        """Callback when connection is established."""
        logger.debug("[DEBUG] IBKRWrapper.nextValidId() called")
        super().nextValidId(orderId)
        self.next_order_id = orderId
        logger.info(f"Connected to IB Gateway. Next valid order ID: {orderId}")
        if self._request_manager:
            logger.debug(f"[DEBUG] Calling _request_manager._on_connected with orderId={orderId}")
            self._request_manager._on_connected(orderId)
            # Start keepalive when connection is established
            if hasattr(self._request_manager, '_client_thread') and self._request_manager._client_thread:
                logger.info("[DEBUG] Starting keepalive timer from nextValidId callback")
                self._request_manager._client_thread._start_keepalive()
        logger.debug("[DEBUG] IBKRWrapper.nextValidId() completed")

    def error(self, reqId: int, errorCode: int, errorString: str):
        """Callback for error messages."""
        super().error(reqId, errorCode, errorString)

        if errorCode in [2104, 2106, 2158]:
            logger.info(f"IB Info [{errorCode}]: {errorString}")
            return

        logger.error(f"IB Error [{errorCode}] ReqId {reqId}: {errorString}")
        self.error_messages.append({
            "reqId": reqId,
            "errorCode": errorCode,
            "errorString": errorString,
        })

        if errorCode == 2100:
            logger.warning("[ERROR-2100] IB Error 2100 detected - Client unsubscribed by IB Gateway")
            if self._request_manager and hasattr(self._request_manager, '_on_connection_lost'):
                logger.info("[ERROR-2100] Triggering reconnection for error 2100")
                self._request_manager._on_connection_lost(errorCode, errorString)
            else:
                logger.error("[ERROR-2100] Cannot trigger reconnection - _request_manager or _on_connection_lost not available")

        if self._request_manager:
            self._request_manager._on_error(reqId, errorCode, errorString)

    def managedAccounts(self, accountsList: str):
        """Callback with list of managed accounts."""
        super().managedAccounts(accountsList)
        self.managed_accounts = accountsList.split(",")
        logger.info(f"Managed accounts: {self.managed_accounts}")

    def accountSummary(self, reqId: int, account: str, tag: str, value: str, currency: str):
        """Callback for account summary data."""
        super().accountSummary(reqId, account, tag, value, currency)
        logger.info(f"Account summary data: reqId={reqId}, account={account}, tag={tag}, value={value}, currency={currency}")
        if account not in self.account_summary:
            self.account_summary[account] = {}
        self.account_summary[account][tag] = value

    def accountSummaryEnd(self, reqId: int):
        """Callback when account summary is complete."""
        super().accountSummaryEnd(reqId)
        if self._request_manager:
            self._request_manager._on_account_summary_complete(reqId)

    def updateAccountValue(self, key: str, val: str, currency: str, accountName: str):
        """Callback for account value updates."""
        super().updateAccountValue(key, val, currency, accountName)
        if accountName not in self.account_values:
            self.account_values[accountName] = {}
        self.account_values[accountName][key] = val

    def accountDownloadEnd(self, accountName: str):
        """Callback when account download is complete."""
        super().accountDownloadEnd(accountName)
        logger.info(f"Account download complete for {accountName}")
        if self._request_manager:
            # Complete any pending get_account_summary requests
            self._request_manager._on_account_download_complete()

    def position(self, account: str, contract: Contract, position: float, avgCost: float):
        """Callback for position data."""
        logger.debug(f"IBKRWrapper.position() called: account={account}, symbol={contract.symbol}, position={position}, avgCost={avgCost}")
        super().position(account, contract, position, avgCost)
        self.positions.append({
            "account": account,
            "symbol": contract.symbol,
            "position": position,
            "avgCost": avgCost,
            "contract": contract
        })
        logger.debug(f"Position stored: {contract.symbol}, total positions count: {len(self.positions)}")

    def positionEnd(self):
        """Callback when all positions have been received."""
        logger.debug(f"IBKRWrapper.positionEnd() called - received {len(self.positions)} positions")
        super().positionEnd()
        if self._request_manager:
            logger.debug(f"Calling _request_manager._on_positions_complete()")
            self._request_manager._on_positions_complete()
        logger.info(f"All positions received from IB: {len(self.positions)} positions")

    def openOrder(self, orderId: int, contract: Contract, order, orderState):
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
        if self._request_manager:
            self._request_manager._on_orders_complete()

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

    def tickPrice(self, reqId: int, tickType: int, price: float, attrib):
        """Callback for market data price tick."""
        super().tickPrice(reqId, tickType, price, attrib)
        if reqId not in self.market_data:
            self.market_data[reqId] = {}
        tick_map = {1: "bid", 2: "ask", 4: "last", 6: "high", 7: "low", 9: "close"}
        if tickType in tick_map:
            self.market_data[reqId][tick_map[tickType]] = price

    def tickSize(self, reqId: int, tickType: int, size: int):
        """Callback for market data size tick."""
        super().tickSize(reqId, tickType, size)
        if reqId not in self.market_data:
            self.market_data[reqId] = {}
        tick_map = {0: "bidSize", 3: "askSize", 5: "lastSize", 8: "volume"}
        if tickType in tick_map:
            self.market_data[reqId][tick_map[tickType]] = size

    def historicalData(self, reqId: int, bar):
        """Callback for historical data bars."""
        super().historicalData(reqId, bar)
        if reqId not in self.historical_data:
            self.historical_data[reqId] = []
        self.historical_data[reqId].append(bar)

    def historicalDataEnd(self, reqId: int, start: str, end: str):
        """Callback when historical data is complete."""
        super().historicalDataEnd(reqId, start, end)
        if self._request_manager:
            self._request_manager._on_historical_data_complete(reqId)


class RequestManager:
    """Manages pending requests and their completion events."""

    def __init__(self) -> None:
        self._pending_requests: Dict[int, Request] = {}
        self._lock = threading.Lock()
        self._next_id = 1
        self._client_thread = None

    def create_request(self, action: str, data: Optional[Dict[str, Any]] = None, request_id: Optional[int] = None) -> Request:
        """Create a new request and add to pending."""
        logger.debug(f"RequestManager.create_request() called: action={action}, request_id={request_id}")
        with self._lock:
            if request_id is None:
                req_id = self._next_id
                self._next_id += 1
            else:
                req_id = request_id

            request = Request(
                request_id=req_id,
                action=action,
                data=data or {},
                event=threading.Event()
            )
            self._pending_requests[req_id] = request
            logger.info(f"Created request {req_id} for action {action}, pending count: {len(self._pending_requests)}")
            return request

    def get_request(self, req_id: int) -> Optional[Request]:
        """Get a pending request by ID."""
        with self._lock:
            return self._pending_requests.get(req_id)

    def complete_request(self, req_id: int, result: Optional[Any] = None, error: Optional[str] = None) -> None:
        """Mark a request as complete with result or error."""
        logger.debug(f"RequestManager.complete_request() called: req_id={req_id}, error={error}")
        with self._lock:
            request = self._pending_requests.get(req_id)
            if request:
                logger.info(f"Completing request {req_id}, action={request.action}")
                request.result = result
                request.error = error
                request.completed = True
                request.event.set()
                logger.info(f"Request {req_id} event set, result size: {len(str(result)) if result else 0} bytes")
            else:
                logger.warning(f"No pending request found for req_id {req_id}")

    def remove_request(self, req_id: int) -> None:
        """Remove a request from pending."""
        with self._lock:
            self._pending_requests.pop(req_id, None)

    def _on_connected(self, order_id: int) -> None:
        """Handle connection callback."""
        for req in list(self._pending_requests.values()):
            if req.action == "connect":
                self.complete_request(req.request_id, result=order_id)

    def _on_error(self, req_id: int, error_code: int, error_string: str) -> None:
        """Handle error callback."""
        if req_id > 0:
            self.complete_request(req_id, error=error_string)

    def _on_account_summary_complete(self, req_id: int) -> None:
        """Handle account summary completion (from reqAccountSummary)."""
        logger.info(f"Account summary complete callback for req_id {req_id}")

    def _on_account_download_complete(self) -> None:
        """Handle account download completion (from reqAccountUpdates)."""
        logger.info("Account download complete")
        for req in list(self._pending_requests.values()):
            if req.action == "get_account_summary":
                self.complete_request(req.request_id)

    def _on_positions_complete(self) -> None:
        """Handle positions completion."""
        logger.debug(f"RequestManager._on_positions_complete() called")
        for req in list(self._pending_requests.values()):
            if req.action == "get_positions":
                logger.debug(f"Completing get_positions request {req.request_id}")
                self.complete_request(req.request_id)
        logger.info(f"Positions completion processed for {len(self._pending_requests)} pending requests")

    def _on_orders_complete(self) -> None:
        """Handle orders completion."""

    def _on_historical_data_complete(self, req_id: int) -> None:
        """Handle historical data completion."""
        self.complete_request(req_id)

    def _on_connection_lost(self, error_code: int, error_string: str) -> None:
        """Handle connection lost callback for reconnection."""
        logger.info(f"[DEBUG] _on_connection_lost() called: error_code={error_code}, error_string={error_string}")
        if hasattr(self, '_client_thread') and self._client_thread:
            logger.info(f"[DEBUG] Connection lost (error {error_code}), initiating reconnection")
            self._client_thread._schedule_reconnect()
        else:
            logger.error("[DEBUG] Cannot reconnect - _client_thread not available")


class IBKRClientThread(threading.Thread):
    """Thread that runs IB API client and handles requests from main thread."""

    def __init__(self, host: str, port: int, client_id: int) -> None:
        logger.debug(f"IBKRClientThread.__init__() called: host={host}, port={port}, client_id={client_id}")
        super().__init__(daemon=True, name="IBKRClientThread")
        self.host = host
        self.port = port
        self.client_id = client_id

        self.request_queue = queue.Queue()
        self.request_manager = RequestManager()
        self.request_manager._client_thread = self

        self.wrapper = IBKRWrapper()
        self.wrapper.set_request_manager(self.request_manager)
        self._request_processor_thread = None

        self._keepalive_timer = None
        self._keepalive_interval = 30
        self._reconnect_backoff = 5
        self._max_reconnect_attempts = 5
        self._reconnect_attempts = 0
        self.client = EClient(self.wrapper)

        self.connected = threading.Event()
        self.running = threading.Event()
        self.connection_error = None
        self._account_updates_subscribed = False
        logger.debug("IBKRClientThread.__init__() completed")

    def get_account_summary(self, req_id: int) -> Request:
        """Request account summary."""
        request = self.request_manager.create_request(
            "get_account_summary",
            {"req_id": req_id},
            request_id=req_id
        )
        logger.info(f"Queuing account summary request {req_id}")
        self.request_queue.put(request)
        logger.info(f"Account summary request {req_id} queued")
        return request

    def get_positions(self) -> Request:
        """Request positions."""
        logger.debug("IBKRClientThread.get_positions() called")
        request = self.request_manager.create_request("get_positions")
        self.request_queue.put(request)
        logger.debug(f"get_positions request queued: req_id={request.request_id}")
        return request

    def get_orders(self) -> Request:
        """Request open orders."""
        request = self.request_manager.create_request("get_orders")
        self.request_queue.put(request)
        return request

    def get_market_price(self, symbol: str, req_id: int) -> Request:
        """Request market price."""
        request = self.request_manager.create_request(
            "get_market_price",
            {"symbol": symbol, "req_id": req_id}
        )
        self.request_queue.put(request)
        return request

    def get_historical_data(self, symbol: str, req_id: int, **kwargs: Any) -> Request:
        """Request historical data."""
        data = {"symbol": symbol, "req_id": req_id, **kwargs}
        request = self.request_manager.create_request("get_historical_data", data)
        self.request_queue.put(request)
        return request

    def stop(self) -> None:
        """Signal thread to stop."""
        logger.debug("[DEBUG] IBKRClientThread.stop() called")
        # Stop keepalive timer
        self._stop_keepalive()
        
        # Cancel account updates subscription if any
        if self._account_updates_subscribed and self.wrapper.managed_accounts:
            try:
                account = self.wrapper.managed_accounts[0]
                self.client.reqAccountUpdates(False, account)
            except Exception:
                pass
        self.running.clear()
        self.request_queue.put(None)
        logger.debug("[DEBUG] IBKRClientThread.stop() completed")

    def _start_keepalive(self) -> None:
        """Start periodic keepalive ping to maintain connection."""
        logger.info("[DEBUG] _start_keepalive() called")
        self._stop_keepalive()
        self._schedule_keepalive()
        logger.info(f"[DEBUG] Keepalive timer started (interval: {self._keepalive_interval}s)")

    def _stop_keepalive(self) -> None:
        """Stop keepalive timer."""
        logger.debug("[DEBUG] _stop_keepalive() called")
        if self._keepalive_timer:
            self._keepalive_timer.cancel()
            self._keepalive_timer = None
            logger.debug("[DEBUG] Keepalive timer stopped")

    def _schedule_keepalive(self) -> None:
        """Schedule next keepalive ping."""
        logger.debug("[DEBUG] _schedule_keepalive() called, running.is_set()={self.running.is_set()}")
        if not self.running.is_set():
            logger.warning("[DEBUG] Keepalive not scheduled - running flag not set")
            return
        
        try:
            self._keepalive_timer = threading.Timer(self._keepalive_interval, self._send_keepalive)
            self._keepalive_timer.daemon = True
            self._keepalive_timer.start()
            logger.debug(f"[DEBUG] Keepalive ping scheduled in {self._keepalive_interval}s")
        except Exception as e:
            logger.error(f"[DEBUG] Error scheduling keepalive: {e}")

    def _send_keepalive(self) -> None:
        """Send keepalive ping to IB Gateway."""
        logger.debug("[DEBUG] _send_keepalive() called")
        try:
            if self.client and self.wrapper.next_order_id is not None:
                logger.info("[KEEPALIVE] Sending keepalive ping (reqCurrentTime)")
                self.client.reqCurrentTime()
                logger.debug("[DEBUG] Keepalive ping sent successfully")
            else:
                logger.warning("[DEBUG] Cannot send keepalive - client not ready, client={self.client is not None}, next_order_id={self.wrapper.next_order_id}")
        except Exception as e:
            logger.error(f"[DEBUG] Error sending keepalive: {e}")
        
        # Schedule next keepalive
        self._schedule_keepalive()

    def _schedule_reconnect(self) -> None:
        """Schedule reconnection after backoff delay."""
        logger.info("[DEBUG] _schedule_reconnect() called")
        if self._reconnect_attempts >= self._max_reconnect_attempts:
            logger.error(f"Max reconnection attempts ({self._max_reconnect_attempts}) reached")
            return
        
        backoff = self._reconnect_backoff * (2 ** min(self._reconnect_attempts, 5))
        logger.info(f"[DEBUG] Scheduling reconnection in {backoff}s (attempt {self._reconnect_attempts + 1})")
        
        def _reconnect():
            logger.info("[DEBUG] Reconnection timer fired - starting reconnection process")
            self._reconnect_attempts += 1
            logger.info(f"[DEBUG] Reconnect attempt {self._reconnect_attempts}/{self._max_reconnect_attempts}")
            
            # Stop current client
            self.running.clear()
            self._stop_keepalive()
            logger.info("[DEBUG] Stopped keepalive and cleared running flag")
            
            try:
                # Wait a moment for cleanup
                threading.Event().wait(1.0)
                
                # Reconnect
                logger.info("[DEBUG] Attempting to connect to IB Gateway...")
                self.client.connect(self.host, self.port, self.client_id)
                logger.info("[DEBUG] Socket connection established")
                
                # Start message loop in a new thread
                def _run_message_loop():
                    logger.info("[DEBUG] Starting message loop thread")
                    try:
                        self.client.run()
                        logger.warning("[DEBUG] Message loop thread exited")
                    except Exception as e:
                        logger.error(f"[DEBUG] Message loop thread error: {e}")
                
                message_thread = threading.Thread(target=_run_message_loop, daemon=True, name="IBKRMessageLoop")
                message_thread.start()
                logger.info("[DEBUG] Message loop thread started")
                
                # Start request processor thread
                self._request_processor_thread = threading.Thread(target=self._process_requests, daemon=True, name="IBKRRequestProcessor")
                self._request_processor_thread.start()
                logger.info("[DEBUG] Request processor thread started")
                
                self.running.set()
                logger.info("[DEBUG] Set running flag")
                
                # Wait for nextValidId callback
                logger.info("[DEBUG] Waiting for nextValidId callback...")
                for _ in range(30):
                    if self.wrapper.next_order_id is not None:
                        break
                    threading.Event().wait(0.1)
                
                if self.wrapper.next_order_id is None:
                    logger.error("[DEBUG] nextValidId not received after reconnect")
                    if self._reconnect_attempts < self._max_reconnect_attempts:
                        self._schedule_reconnect()
                    return
                
                logger.info(f"[DEBUG] nextValidId received: {self.wrapper.next_order_id}")
                
                # Reset reconnect attempts on success
                self._reconnect_attempts = 0
                logger.info("[DEBUG] Reset reconnect attempts counter")
                
                # Start keepalive
                self._start_keepalive()
                logger.info("[DEBUG] Keepalive timer started after reconnect")
                
                # Re-establish account updates subscription
                if self.wrapper.managed_accounts:
                    account = self.wrapper.managed_accounts[0]
                    self.client.reqAccountUpdates(True, account)
                    logger.info(f"[DEBUG] Re-established account updates for {account}")
                
                logger.info("[DEBUG] Reconnection completed successfully")
                
            except Exception as e:
                logger.error(f"[DEBUG] Reconnection failed: {e}")
                import traceback
                logger.error(f"[DEBUG] Traceback: {traceback.format_exc()}")
                if self._reconnect_attempts < self._max_reconnect_attempts:
                    # Try again with exponential backoff
                    self._schedule_reconnect()
        
        threading.Timer(backoff, _reconnect).start()
        logger.info("[DEBUG] Reconnect timer scheduled")

    def run(self) -> None:
        """Main thread loop - runs IB API client and processes requests."""
        import traceback
        logger.info(f"IBKRClientThread starting on {self.host}:{self.port}")

        try:
            self.client.connect(self.host, self.port, self.client_id)
            logger.info(f"Connected to IB Gateway, starting message loop...")
            self.running.set()
            self.connected.set()

            # Start a separate thread for processing the request queue
            self._request_processor_thread = threading.Thread(target=self._process_requests, daemon=True, name="IBKRRequestProcessor")
            self._request_processor_thread.start()
            logger.debug("Request processor thread spawned")

            # Run the IB client message loop in this thread
            logger.debug("Starting IB client.run() message loop")
            self.client.run()

            logger.info("IBKRClientThread message loop ended, shutting down...")

        except Exception as e:
            logger.error(f"IBKRClientThread error: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            self.connection_error = str(e)
            self.connected.clear()
            self.running.clear()

    def _process_requests(self) -> None:
        """Process requests from the request queue."""
        import traceback
        logger.info("Request processor thread started")
        while self.running.is_set():
            try:
                request = self.request_queue.get(timeout=0.1)
                if request is None:
                    break

                logger.debug(f"Processing request: {request.action}, req_id={request.request_id}")
                self._handle_request(request)
                self.request_queue.task_done()
                logger.debug(f"Request completed: {request.action}")
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error in _process_requests: {e}")
                logger.error(f"Traceback: {traceback.format_exc()}")
        logger.info("Request processor thread stopped")

    def _handle_request(self, request: Request) -> None:
        """Handle a request from the main thread."""
        import traceback
        action = request.action
        logger.debug(f"IBKRClientThread._handle_request() called: action={action}, req_id={request.request_id}")

        try:
            if action == "get_account_summary":
                req_id = request.data["req_id"]
                logger.debug(f"Handling get_account_summary request {req_id}")
                # Cancel previous account updates subscription if any
                if self._account_updates_subscribed:
                    try:
                        account = self.wrapper.managed_accounts[0] if self.wrapper.managed_accounts else ""
                        self.client.reqAccountUpdates(False, account)
                        logger.debug(f"Cancelled previous account updates for {account}")
                    except Exception:
                        pass
                # Request new account updates
                account = self.wrapper.managed_accounts[0] if self.wrapper.managed_accounts else ""
                self.client.reqAccountUpdates(True, account)
                self._account_updates_subscribed = True
                logger.info(f"Requested account updates for {account}, req_id={req_id}")

            elif action == "get_positions":
                logger.debug(f"Handling get_positions request {request.request_id}")
                self.wrapper.positions.clear()
                self.client.reqPositions()
                logger.info(f"Sent reqPositions() request, req_id={request.request_id}")

            elif action == "get_orders":
                logger.debug(f"Handling get_orders request {request.request_id}")
                self.wrapper.open_orders.clear()
                self.client.reqAllOpenOrders()
                logger.info(f"Sent reqAllOpenOrders() request, req_id={request.request_id}")

            elif action == "get_market_price":
                symbol = request.data["symbol"]
                req_id = request.data["req_id"]
                logger.debug(f"Handling get_market_price request for {symbol}, req_id={req_id}")
                contract = Contract()
                contract.symbol = symbol
                contract.secType = "STK"
                contract.exchange = "SMART"
                contract.currency = "USD"
                self.wrapper.market_data[req_id] = {}
                self.client.reqMktData(req_id, contract, "", False, False, [])
                logger.info(f"Sent reqMktData() for {symbol}, req_id={req_id}")

            elif action == "get_historical_data":
                symbol = request.data["symbol"]
                req_id = request.data["req_id"]
                duration = request.data.get("duration", "1 D")
                bar_size = request.data.get("bar_size", "1 min")
                what_to_show = request.data.get("what_to_show", "TRADES")
                end_date = request.data.get("end_date", "")
                logger.debug(f"Handling get_historical_data request for {symbol}, req_id={req_id}, duration={duration}")

                contract = Contract()
                contract.symbol = symbol
                contract.secType = "STK"
                contract.exchange = "SMART"
                contract.currency = "USD"

                self.wrapper.historical_data[req_id] = []
                self.client.reqHistoricalData(
                    req_id, contract, end_date, duration, bar_size,
                    what_to_show, 1, 1, False, []
                )
                logger.info(f"Sent reqHistoricalData() for {symbol}, req_id={req_id}")

        except Exception as e:
            logger.error(f"Error handling request {request.action}: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            self.request_manager.complete_request(request.request_id, error=str(e))
