# TradeMind AI - IB Gateway Integration System Design

## 1. Architecture Overview

### 1.1 High-Level System Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              TRADEMIND AI                                    │
│                         FastAPI Application Layer                           │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ async/await
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         IBKRThreadedBroker                                  │
│                    (Async Wrapper - BaseBroker)                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  Methods:                                                                    │
│  • connect()                    • disconnect()                              │
│  • get_account()                • get_positions()                           │
│  • place_order()                • cancel_order()                            │
│  • get_orders()                 • get_market_price()                        │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ asyncio.to_thread()
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         IBKRClientThread                                    │
│                  (Threading.Thread - Daemon)                                │
├─────────────────────────────────────────────────────────────────────────────┤
│  Components:                                                                 │
│  • request_queue (Queue)        • client (EClient)                          │
│  • request_manager              • wrapper (IBKRWrapper)                     │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ IB API Calls (Socket)
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         IB Gateway                                          │
│                  (127.0.0.1:7497/7496)                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│  Ports:                                                                      │
│  • 7497: Paper Trading                                                     │
│  • 7496: Live Trading                                                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ HTTPS
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      Interactive Brokers                                    │
│                     (Live/Paper Accounts)                                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Component Interactions

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   FastAPI   │────▶│  Request    │────▶│   Thread    │────▶│   IB API    │
│   Routes    │     │   Queue     │     │  Processor  │     │   Client    │
└─────────────┘     └─────────────┘     └─────────────┘     └──────┬──────┘
       │                                                             │
       │                    Response Flow                            │
       │                                                             │
       │◀────────────────────────────────────────────────────────────┘
       │                    (via threading.Event)
       │
       ▼
┌─────────────┐
│   JSON      │
│  Response   │
└─────────────┘
```

## 2. Thread-Based IB Client

### 2.1 Why Thread-Based Design?

**Problem:** The IBKR Python API (`ibapi`) is **synchronous and blocking**:
- `client.run()` blocks the thread forever
- Callbacks execute in the same thread
- Direct integration with FastAPI's async event loop causes conflicts

**Solution:** Thread-based architecture with clean separation:
```python
# Thread 1: FastAPI Event Loop (Main Thread)
#   - Handles HTTP requests
#   - Uses async/await
#   - Calls IBKRThreadedBroker methods

# Thread 2: IBKRClientThread (Daemon Thread)
#   - Runs IB API client
#   - Processes requests from queue
#   - Handles all IB callbacks
```

### 2.2 Request/Response Flow

```
┌────────────────────────────────────────────────────────────────────────┐
│                        REQUEST FLOW                                     │
└────────────────────────────────────────────────────────────────────────┘

1. FastAPI Route receives HTTP request
   └─▶ calls await ibkr.get_account()

2. IBKRThreadedBroker.create_request()
   └─▶ Creates Request object with threading.Event

3. Request placed in thread-safe queue
   └─▶ self.request_queue.put(request)

4. IBKRClientThread processes request
   └─▶ _handle_request(request)

5. IB API call made
   └─▶ self.client.reqAccountUpdates(True, account)

6. Callback received (IBKRWrapper)
   └─▶ accountDownloadEnd()

7. Request marked complete
   └─▶ request_manager.complete_request(req_id)

8. threading.Event.set() signals completion

9. FastAPI async wait returns
   └─▶ await asyncio.to_thread(request.event.wait)

10. Response returned to client
    └─▶ JSON with account data
```

### 2.3 Key Classes

#### IBKRClientThread
```python
class IBKRClientThread(threading.Thread):
    """Runs IB API client in dedicated daemon thread."""
    
    def __init__(self, host: str, port: int, client_id: int):
        super().__init__(daemon=True)
        self.host = host
        self.port = port
        self.client_id = client_id
        self.request_queue = queue.Queue()
        self.request_manager = RequestManager()
        self.wrapper = IBKRWrapper()
        self.client = EClient(self.wrapper)
```

#### RequestManager
```python
class RequestManager:
    """Thread-safe request tracking with completion events."""
    
    def __init__(self):
        self._pending_requests: Dict[int, Request] = {}
        self._lock = threading.Lock()
    
    def create_request(self, action: str, data: Optional[Dict] = None) -> Request:
        with self._lock:
            # Thread-safe request creation
            
    def complete_request(self, req_id: int, result: Any = None, error: str = None):
        with self._lock:
            # Mark request complete and signal event
```

#### Request
```python
@dataclass
class Request:
    """Represents a request from main thread to IB client thread."""
    request_id: int
    action: str                    # e.g., "get_account", "place_order"
    data: Optional[Dict[str, Any]] # Request parameters
    event: threading.Event         # Signals completion
    result: Any = None             # Response data
    error: Optional[str] = None    # Error message
    timestamp: datetime = field(default_factory=datetime.utcnow)
```

## 3. Async Wrapper

### 3.1 Bridging Sync and Async

The `IBKRThreadedBroker` class bridges the synchronous IB API with FastAPI's async framework:

```python
class IBKRThreadedBroker(BaseBroker):
    """Async wrapper around threaded IBKR client."""
    
    async def get_account(self) -> Account:
        """Get account information asynchronously."""
        if not self.is_connected:
            raise ConnectionError("Not connected to IBKR")
        
        # Create request in thread
        request = self._thread.get_account_summary(req_id)
        
        # Wait for completion asynchronously
        await self._wait_for_request(request, timeout=10.0)
        
        # Extract and return account data
        return self._extract_account_from_wrapper()
```

### 3.2 Method Mapping

| Async Method (IBKRThreadedBroker) | Thread Method (IBKRClientThread) | IB API Call |
|-----------------------------------|----------------------------------|-------------|
| `connect()` | `run()` | `client.connect()` |
| `get_account()` | `get_account_summary()` | `reqAccountUpdates()` |
| `get_positions()` | `get_positions()` | `reqPositions()` |
| `place_order()` | Lambda via `to_thread()` | `placeOrder()` |
| `cancel_order()` | Lambda via `to_thread()` | `cancelOrder()` |
| `get_orders()` | `get_orders()` | `reqAllOpenOrders()` |

### 3.3 Async-to-Thread Bridge

```python
async def _wait_for_request(self, request: Request, timeout: float = 10.0) -> Any:
    """Wait for a request to complete in the thread."""
    try:
        await asyncio.wait_for(
            asyncio.to_thread(request.event.wait),
            timeout=timeout
        )
    except asyncio.TimeoutError:
        self._thread.request_manager.remove_request(request.request_id)
        raise TimeoutError(f"Request {request.action} timed out")
    
    if request.error:
        raise RuntimeError(request.error)
    
    return request.result
```

## 4. Integration Layer

### 4.1 Singleton Pattern

```python
class IBKRIntegration:
    """Manages integration between TradeMind and IB Gateway."""
    
    _instance = None
    _lock = threading.Lock()
    _broker = None
    _connected = False
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
```

**Benefits:**
- Single global point of access
- Lazy initialization (connects only when needed)
- Thread-safe instance creation
- Prevents multiple connections to IB Gateway

### 4.2 Connection Management

```python
async def ensure_connected(self) -> bool:
    """Ensure connection to IB Gateway (lazy connection)."""
    if not settings.ibkr_enabled:
        return False
    
    # Initialize broker if not already done
    if not self._broker:
        await self.connect()
    
    if self._connected:
        return True
    
    try:
        await self._broker.connect()
        self._connected = True
        logger.info(f"✅ Connected to IB Gateway on port {settings.ibkr_port}")
        return True
    except Exception as e:
        logger.error(f"❌ IBKR connection error: {e}")
        return False
```

### 4.3 Portfolio Synchronization

```python
async def sync_portfolio(self, db: Session = None) -> Dict:
    """Sync TradeMind portfolio with IB Gateway account."""
    if not await self.ensure_connected():
        return {"success": False, "error": "Not connected"}
    
    # Get IB account info
    account = await self._broker.get_account()
    positions = await self._broker.get_positions()
    
    # Update database
    snapshot = PortfolioSnapshot(
        timestamp=datetime.utcnow(),
        total_value=account.portfolio_value,
        cash_balance=account.cash_balance,
        invested_value=account.portfolio_value - account.cash_balance,
        daily_pnl=0.0,
        total_return_pct=0.0
    )
    db.add(snapshot)
    
    # Sync holdings
    ib_symbols = {pos.symbol for pos in positions}
    db.query(Holding).filter(Holding.symbol.in_(ib_symbols)).delete(
        synchronize_session=False
    )
    
    for pos in positions:
        holding = Holding(
            symbol=pos.symbol,
            quantity=pos.quantity,
            avg_cost=pos.avg_cost,
            # ...
        )
        db.add(holding)
    
    db.commit()
```

## 5. Data Flow Examples

### 5.1 Account Information Retrieval

```
┌─────────────────────────────────────────────────────────────────────┐
│                    ACCOUNT RETRIEVAL FLOW                           │
└─────────────────────────────────────────────────────────────────────┘

Step 1: HTTP Request
┌──────────┐    GET /api/portfolio/account    ┌──────────┐
│  Client  │ ─────────────────────────────────▶ │  FastAPI │
└──────────┘                                    └──────────┘
                                                      │
Step 2: Async Broker Call                             ▼
┌──────────┐    await ibkr.get_account()       ┌──────────┐
│  FastAPI │ ─────────────────────────────────▶ │ IBKR     │
└──────────┘                                    │ Threaded │
                                                │ Broker   │
                                                └──────────┘
                                                      │
Step 3: Create Request                                ▼
┌──────────┐    Request("get_account")         ┌──────────┐
│ IBKR     │ ─────────────────────────────────▶ │ Request  │
│ Threaded │                                    │ Manager  │
│ Broker   │                                    └──────────┘
└──────────┘                                          │
                                                      ▼
Step 4: Queue Request                           ┌──────────┐
┌──────────┐    queue.put(request)             │ Thread   │
│ Request  │ ─────────────────────────────────▶ │ Queue    │
│ Manager  │                                    └──────────┘
└──────────┘                                          │
                                                      ▼
Step 5: Process Request                         ┌──────────┐
┌──────────┐    _handle_request()              │ IBKR     │
│ Thread   │ ─────────────────────────────────▶ │ Client   │
│ Queue    │                                    │ Thread   │
└──────────┘                                    └──────────┘
                                                      │
Step 6: IB API Call                                 ┌──────┴───┐
┌──────────┐    reqAccountUpdates()              │   IB     │
│ IBKR     │ ───────────────────────────────────▶│  Gateway │
│ Client   │                                      │  7497    │
│ Thread   │                                      └──────────┘
└──────────┘                                            │
                                                      Callback
Step 7: Callback Received                             ▼
┌──────────┐    accountDownloadEnd()             ┌──────────┐
│  IBKR    │ ◀────────────────────────────────── │  IBKR    │
│ Wrapper  │                                     │ Wrapper  │
└──────────┘                                     └──────────┘
      │
Step 8: Complete Request                             ▼
┌──────────┐    complete_request()               ┌──────────┐
│  IBKR    │ ──────────────────────────────────▶ │ Request  │
│ Wrapper  │                                     │ Manager  │
└──────────┘                                     └──────────┘
                                                        │
Step 9: Signal Completion                               ▼
┌──────────┐    event.set()                        ┌────────┐
│ Request  │ ───────────────────────────────────▶ │ Event  │
│ Manager  │                                       │ Set    │
└──────────┘                                       └────────┘
      │
Step 10: Async Wait Returns                           ▼
┌──────────┐    await asyncio.to_thread()        ┌──────────┐
│ IBKR     │ ◀───────────────────────────────── │ Asyncio  │
│ Threaded │                                      │ Thread   │
│ Broker   │                                      └──────────┘
└──────────┘
      │
Step 11: JSON Response                                ▼
┌──────────┐    {"account": {...}}                ┌──────────┐
│  FastAPI │ ──────────────────────────────────▶ │  Client  │
└──────────┘                                      └──────────┘
```

### 5.2 Order Placement Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                    ORDER PLACEMENT FLOW                             │
└─────────────────────────────────────────────────────────────────────┘

Step 1: HTTP POST
┌──────────┐    POST /api/orders                  ┌──────────┐
│  Client  │ ────────────────────────────────────▶ │  FastAPI │
└──────────┘                                      └──────────┘
                                                        │
Step 2: Validate Order                                  ▼
┌──────────┐    Validate symbol, quantity, price     ┌──────────┐
│  FastAPI │ ──────────────────────────────────────▶ │  Risk    │
└──────────┘                                         │  Manager │
                                                     └──────────┘
                                                           │
Step 3: Async Place Order                                  ▼
┌──────────┐    await place_order(order)              ┌──────────┐
│  FastAPI │ ───────────────────────────────────────▶ │ IBKR     │
└──────────┘                                         │ Threaded │
                                                     │ Broker   │
                                                     └──────────┘
                                                           │
Step 4: Direct IB API Call (No Queue)                      ▼
┌──────────┐    asyncio.to_thread(lambda ...)         ┌──────────┐
│ IBKR     │ ───────────────────────────────────────▶ │  Lambda  │
│ Threaded │                                          │ Function │
│ Broker   │                                          └──────────┘
└──────────┘                                                │
                                                            ▼
Step 5: Execute in Thread                              ┌──────────┐
┌──────────┐    client.placeOrder()                   │ IBKR     │
│  Lambda  │ ───────────────────────────────────────▶ │ Client   │
│ Function │                                          │ Thread   │
└──────────┘                                          └──────────┘
                                                            │
Step 6: Send to IB Gateway                                   │
┌──────────┐    Socket communication                  ┌──────────┐
│ IBKR     │ ───────────────────────────────────────▶ │   IB     │
│ Client   │                                          │ Gateway  │
│ Thread   │                                          │  7497    │
└──────────┘                                          └──────────┘
                                                            │
Step 7: Order Confirmation                                Callback
┌──────────┐    orderStatus()                        ┌──────────┐
│  IBKR    │ ◀───────────────────────────────────── │   IB     │
│ Wrapper  │                                         │ Gateway  │
└──────────┘                                         └──────────┘
      │
Step 8: Update Order Status                            ▼
┌──────────┐    Update order in _orders dict         ┌──────────┐
│  IBKR    │ ─────────────────────────────────────▶ │  Order   │
│ Wrapper  │                                         │  Store   │
└──────────┘                                         └──────────┘
      │
Step 9: Return Order ID                                 ▼
┌──────────┐    {"order_id": "12345"}                ┌──────────┐
│  FastAPI │ ──────────────────────────────────────▶ │  Client  │
└──────────┘                                         └──────────┘
```

## 6. Security Considerations

### 6.1 Credentials Management

```yaml
# .env (DO NOT COMMIT)
IBKR_ACCOUNT=DU1234567        # Account ID
IBKR_CLIENT_ID=1              # Unique client ID per connection

# Never store IBKR username/password in code
# Use IB Gateway's saved credentials or manual login
```

### 6.2 Paper vs Live Trading

| Feature | Paper Trading (Port 7497) | Live Trading (Port 7496) |
|---------|---------------------------|--------------------------|
| Risk | No real money | Real money at risk |
| Testing | ✅ Safe for all tests | ❌ Only production |
| Orders | Simulated fills | Real market fills |
| Latency | Higher | Lower |
| Data | Delayed 15 min | Real-time (subscription) |

**Recommendation:** Always use paper trading for development and testing.

### 6.3 Order Validation

```python
def validate_order(self, order: Order) -> Tuple[bool, str]:
    """Validate order before submission."""
    
    # Check connection
    if not self.is_connected:
        return False, "Not connected to IBKR"
    
    # Check order value
    order_value = order.quantity * order.price
    if order_value > self.max_order_value:
        return False, f"Order value ${order_value} exceeds limit"
    
    # Check daily order count
    if self.daily_orders >= self.max_daily_orders:
        return False, "Daily order limit reached"
    
    # Check symbol validity
    if not self.is_valid_symbol(order.symbol):
        return False, f"Invalid symbol: {order.symbol}"
    
    return True, "Order valid"
```

## 7. Performance

### 7.1 Thread Management

| Resource | Configuration | Notes |
|----------|---------------|-------|
| IB Client Thread | 1 daemon thread | Dedicated to IB API |
| Request Processor | 1 thread per client | Processes queue |
| Thread Pool | Default asyncio | For `to_thread()` calls |

### 7.2 Queue Sizing

```python
# Unlimited queue (memory-constrained)
self.request_queue = queue.Queue()  # No maxsize

# Alternative: Bounded queue for backpressure
self.request_queue = queue.Queue(maxsize=100)
```

### 7.3 Timeout Handling

| Operation | Timeout | Rationale |
|-----------|---------|-----------|
| Connection | 10s | IB Gateway startup time |
| Account info | 10s | Account data retrieval |
| Order placement | 5s | Quick order submission |
| Position sync | 10s | Position data retrieval |
| Market data | 5s | Real-time data fetch |

### 7.4 Latency Considerations

```
Typical Latency Breakdown:
├── HTTP Request Processing:     1-5 ms
├── Async Wrapper Overhead:      0.1 ms
├── Queue Wait (avg):            1-10 ms
├── IB API Call:                 10-50 ms
├── IB Gateway → IB Server:      50-200 ms
├── IB Server Response:          50-500 ms
└── Total (round-trip):          100-800 ms
```

## 8. Error Handling

### 8.1 Error Categories

| Category | Examples | Handling |
|----------|----------|----------|
| Connection | Refused, timeout | Retry with backoff |
| Authentication | Invalid client ID | Use unique ID |
| Validation | Invalid symbol | Pre-validation |
| IB API | Error codes 200-599 | Log and propagate |
| Network | Socket errors | Retry logic |

### 8.2 Retry Logic

```python
async def connect_with_retry(self, max_attempts: int = 3) -> bool:
    """Connect with exponential backoff retry."""
    for attempt in range(max_attempts):
        try:
            await self.connect()
            return True
        except ConnectionError as e:
            if attempt < max_attempts - 1:
                delay = 2 ** attempt  # 1s, 2s, 4s
                logger.warning(f"Connection failed, retrying in {delay}s...")
                await asyncio.sleep(delay)
            else:
                raise
    return False
```

## 9. Testing Strategy

### 9.1 Test Pyramid

```
                    ┌─────────────┐
                    │   E2E Tests │  (1-2 tests)
                    │  (IB Gateway│
                    │   required) │
                    └──────┬──────┘
                           │
                    ┌──────┴──────┐
                    │ Integration │  (5-10 tests)
                    │    Tests    │
                    │ (IB Gateway │
                    │   required) │
                    └──────┬──────┘
                           │
               ┌───────────┴───────────┐
               │      Unit Tests       │  (20-30 tests)
               │  (Mocked IB Gateway)  │
               └───────────────────────┘
```

### 9.2 Mock IB Gateway

```python
@pytest.fixture
def mock_ib_client():
    """Mock IB client for unit tests."""
    with patch('src.brokers.ibkr.threaded_client.EClient') as mock:
        client = mock.return_value
        client.isConnected.return_value = True
        yield client

def test_get_account_mocked(mock_ib_client):
    """Test account retrieval with mocked IB client."""
    broker = IBKRThreadedBroker()
    # Test implementation...
```

## 10. Future Enhancements

### 10.1 Planned Features

| Feature | Priority | Description |
|---------|----------|-------------|
| WebSocket Streaming | High | Real-time market data via WebSocket |
| Order Book Depth | Medium | L2 market data integration |
| Options Trading | Medium | Options order support |
| Multi-Account | Low | Support for multiple IB accounts |
| Auto-Reconnect | High | Automatic reconnection on failure |

### 10.2 Known Limitations

1. **Single Connection**: Only one IB client connection at a time
2. **No WebSocket**: HTTP polling for real-time data
3. **Delayed Data**: Free tier uses 15-min delayed market data
4. **Rate Limits**: IB API has rate limits for market data

## 11. References

### 11.1 IB API Documentation

- [IB API Reference](https://interactivebrokers.github.io/tws-api/)
- [IB Gateway Guide](https://www.interactivebrokers.com/en/index.php?f=16457)
- [API Error Codes](https://interactivebrokers.github.io/tws-api/message_codes.html)

### 11.2 TradeMind Documentation

- [README.md](./README.md) - Project overview
- [IB_GATEWAY_DEBUG_PLAN.md](./IB_GATEWAY_DEBUG_PLAN.md) - Debugging guide
- [IBKR_INTEGRATION_PLAN.md](./IBKR_INTEGRATION_PLAN.md) - Implementation plan

---

**Document Version:** 1.0  
**Last Updated:** 2026-02-10  
**Author:** OpenCode (GLM-4.7)  
**Status:** Complete