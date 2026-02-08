# Interactive Brokers (IBKR) Integration Plan

## Overview

Integrate TradeMind AI with Interactive Brokers for production-grade algorithmic trading. IBKR provides institutional-quality execution, global market access, and multiple API options.

---

## IBKR API Options

### 1. Trader Workstation (TWS) API ⭐ Recommended
- **Type**: Local TCP connection to TWS/IB Gateway
- **Best For**: Real-time trading, low latency
- **Protocol**: Proprietary socket protocol
- **Python Library**: `ib_insync` (async wrapper) or official `ibapi`
- **Requirements**: TWS or IB Gateway running locally

### 2. Client Portal Web API
- **Type**: REST API via web portal
- **Best For**: Simple integrations, web-based
- **Protocol**: HTTPS REST + WebSocket
- **Python Library**: Custom requests + WebSocket
- **Requirements**: Authentication via web login

### 3. FIX API
- **Type**: Financial Information eXchange protocol
- **Best For**: Institutional, high-frequency
- **Protocol**: FIX 4.2/4.4
- **Requirements**: Special approval, higher costs

**Decision**: Use **TWS API with ib_insync** for TradeMind

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    TradeMind AI                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           Broker Interface (Abstract)                 │  │
│  │  - connect()                                          │  │
│  │  - place_order()                                      │  │
│  │  - cancel_order()                                     │  │
│  │  - get_positions()                                    │  │
│  │  - get_account()                                      │  │
│  │  - get_portfolio()                                    │  │
│  └──────────────────────────────────────────────────────┘  │
│                         │                                    │
│                         ▼                                    │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         Interactive Brokers Implementation            │  │
│  │  - IBKRBroker class                                   │  │
│  │  - Async connection management                        │  │
│  │  - Order routing                                      │  │
│  │  - Position tracking                                  │  │
│  │  - Account sync                                       │  │
│  └──────────────────────────────────────────────────────┘  │
│                         │                                    │
│                         ▼                                    │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              ib_insync Library                        │  │
│  │  - Async wrapper around IB API                        │  │
│  │  - Event-driven architecture                          │  │
│  │  - Automatic reconnection                             │  │
│  └──────────────────────────────────────────────────────┘  │
│                         │                                    │
│                         ▼                                    │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           TWS / IB Gateway (Local)                    │  │
│  │  - Port 7496 (live) or 7497 (paper)                   │  │
│  └──────────────────────────────────────────────────────┘  │
│                         │                                    │
│                         ▼                                    │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           Interactive Brokers Servers                 │  │
│  │  - Order execution                                    │  │
│  │  - Market data                                        │  │
│  │  - Account management                                 │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## File Structure

```
trading-agent/
├── src/
│   ├── brokers/                      # NEW: Broker integrations
│   │   ├── __init__.py
│   │   ├── base.py                   # Abstract broker interface
│   │   ├── ibkr/                     # IBKR-specific implementation
│   │   │   ├── __init__.py
│   │   │   ├── client.py             # IBKRBroker class
│   │   │   ├── orders.py             # Order construction helpers
│   │   │   ├── positions.py          # Position tracking
│   │   │   ├── account.py            # Account info
│   │   │   ├── market_data.py        # Market data streaming
│   │   │   └── utils.py              # Utility functions
│   │   └── paper/                    # Existing paper trading
│   │       ├── __init__.py
│   │       └── client.py
│   ├── execution/
│   │   ├── __init__.py
│   │   ├── router.py                 # Route orders to broker
│   │   └── factory.py                # Broker factory
│   └── config.py                     # Add IBKR settings
├── config/
│   └── ibkr_config.yaml              # IBKR-specific config
├── tests/
│   └── brokers/
│       ├── test_ibkr_client.py
│       └── test_order_routing.py
└── docs/
    └── IBKR_SETUP.md                 # Setup instructions
```

---

## Implementation Phases

### Phase 1: Foundation (Week 1)

#### 1.1 Setup & Dependencies
- [ ] Add `ib_insync` to requirements.txt
- [ ] Install TWS or IB Gateway
- [ ] Create paper trading account
- [ ] Configure API settings in TWS
- [ ] Test basic connection

**TWS API Settings:**
```
Edit > Global Configuration > API > Settings
- Enable "ActiveX and Socket Clients": YES
- Socket port: 7497 (paper) / 7496 (live)
- Allow connections from localhost only: NO (for Docker)
- Create trusted IP: 127.0.0.1
- Read-Only API: NO (to allow trading)
```

#### 1.2 Abstract Broker Interface
```python
# src/brokers/base.py
from abc import ABC, abstractmethod
from typing import List, Optional, Dict
from dataclasses import dataclass
from decimal import Decimal

@dataclass
class Order:
    symbol: str
    quantity: int
    side: str  # 'BUY' or 'SELL'
    order_type: str = 'MARKET'  # MARKET, LIMIT, STOP
    limit_price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None
    time_in_force: str = 'DAY'

@dataclass
class Position:
    symbol: str
    quantity: int
    avg_cost: Decimal
    market_price: Decimal
    market_value: Decimal
    unrealized_pnl: Decimal

@dataclass
class Account:
    account_id: str
    cash_balance: Decimal
    portfolio_value: Decimal
    buying_power: Decimal
    day_trades_remaining: int

class BaseBroker(ABC):
    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to broker"""
        pass
    
    @abstractmethod
    async def disconnect(self):
        """Close connection"""
        pass
    
    @abstractmethod
    async def place_order(self, order: Order) -> Dict:
        """Place an order, return order details"""
        pass
    
    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order"""
        pass
    
    @abstractmethod
    async def get_positions(self) -> List[Position]:
        """Get current positions"""
        pass
    
    @abstractmethod
    async def get_account(self) -> Account:
        """Get account information"""
        pass
    
    @abstractmethod
    async def get_orders(self, status: str = 'open') -> List[Dict]:
        """Get orders by status (open, filled, cancelled)"""
        pass
```

#### 1.3 IBKR Connection Manager
```python
# src/brokers/ibkr/client.py
from ib_insync import IB, Stock, MarketOrder, LimitOrder
from src.brokers.base import BaseBroker, Order, Position, Account

class IBKRBroker(BaseBroker):
    def __init__(self, host: str = '127.0.0.1', 
                 port: int = 7497,  # 7497=paper, 7496=live
                 client_id: int = 1):
        self.ib = IB()
        self.host = host
        self.port = port
        self.client_id = client_id
        self._connected = False
    
    async def connect(self) -> bool:
        """Connect to TWS/IB Gateway"""
        try:
            await self.ib.connectAsync(
                host=self.host,
                port=self.port,
                clientId=self.client_id
            )
            self._connected = True
            return True
        except Exception as e:
            logger.error(f"IBKR connection failed: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from TWS"""
        if self._connected:
            self.ib.disconnect()
            self._connected = False
```

---

### Phase 2: Order Management (Week 2)

#### 2.1 Order Types Mapping
| TradeMind Order | IBKR Order Type |
|----------------|-----------------|
| MARKET | MarketOrder |
| LIMIT | LimitOrder |
| STOP | StopOrder |
| STOP_LIMIT | StopLimitOrder |

```python
# src/brokers/ibkr/orders.py
from ib_insync import MarketOrder, LimitOrder, StopOrder
from src.brokers.base import Order

def create_ibkr_order(order: Order):
    """Convert TradeMind Order to IBKR order"""
    contract = Stock(order.symbol, 'SMART', 'USD')
    
    if order.order_type == 'MARKET':
        return MarketOrder(
            action=order.side,
            totalQuantity=order.quantity
        ), contract
    
    elif order.order_type == 'LIMIT':
        return LimitOrder(
            action=order.side,
            totalQuantity=order.quantity,
            lmtPrice=float(order.limit_price)
        ), contract
    
    elif order.order_type == 'STOP':
        return StopOrder(
            action=order.side,
            totalQuantity=order.quantity,
            stopPrice=float(order.stop_price)
        ), contract
```

#### 2.2 Order Execution
```python
# src/brokers/ibkr/client.py (continued)

async def place_order(self, order: Order) -> Dict:
    """Place order with IBKR"""
    ib_order, contract = create_ibkr_order(order)
    
    # Qualify contract
    qualified_contracts = await self.ib.qualifyContractsAsync(contract)
    if not qualified_contracts:
        raise ValueError(f"Could not qualify contract for {order.symbol}")
    
    contract = qualified_contracts[0]
    
    # Place order
    trade = self.ib.placeOrder(contract, ib_order)
    
    return {
        'order_id': trade.order.orderId,
        'status': trade.orderStatus.status,
        'filled': trade.orderStatus.filled,
        'remaining': trade.orderStatus.remaining,
        'avg_fill_price': trade.orderStatus.avgFillPrice
    }

async def cancel_order(self, order_id: str) -> bool:
    """Cancel order by ID"""
    try:
        self.ib.cancelOrder(order_id)
        return True
    except Exception as e:
        logger.error(f"Failed to cancel order {order_id}: {e}")
        return False
```

#### 2.3 Order Tracking
```python
# src/brokers/ibkr/client.py (continued)

async def get_orders(self, status: str = 'open') -> List[Dict]:
    """Get orders from IBKR"""
    trades = self.ib.trades()
    orders = []
    
    for trade in trades:
        order_status = trade.orderStatus.status
        
        # Filter by status
        if status == 'open' and order_status not in ['PendingSubmit', 'PreSubmitted', 'Submitted']:
            continue
        if status == 'filled' and order_status != 'Filled':
            continue
        
        orders.append({
            'order_id': trade.order.orderId,
            'symbol': trade.contract.symbol,
            'action': trade.order.action,
            'quantity': trade.order.totalQuantity,
            'status': order_status,
            'filled': trade.orderStatus.filled,
            'avg_fill_price': trade.orderStatus.avgFillPrice
        })
    
    return orders
```

---

### Phase 3: Portfolio & Account (Week 3)

#### 3.1 Position Sync
```python
# src/brokers/ibkr/positions.py

async def get_positions(self) -> List[Position]:
    """Get current positions from IBKR"""
    positions = self.ib.positions()
    result = []
    
    for pos in positions:
        # Get current market price
        ticker = self.ib.reqMktData(pos.contract)
        await asyncio.sleep(0.1)  # Allow price to arrive
        
        market_price = ticker.last or ticker.close
        if market_price:
            market_value = market_price * pos.position
            unrealized_pnl = market_value - (pos.avgCost * pos.position)
        else:
            market_value = 0
            unrealized_pnl = 0
        
        result.append(Position(
            symbol=pos.contract.symbol,
            quantity=int(pos.position),
            avg_cost=Decimal(str(pos.avgCost)),
            market_price=Decimal(str(market_price)) if market_price else Decimal('0'),
            market_value=Decimal(str(market_value)),
            unrealized_pnl=Decimal(str(unrealized_pnl))
        ))
    
    return result
```

#### 3.2 Account Information
```python
# src/brokers/ibkr/account.py

async def get_account(self) -> Account:
    """Get account summary from IBKR"""
    account_values = self.ib.accountValues()
    
    # Extract key values
    values = {av.tag: av.value for av in account_values}
    
    return Account(
        account_id=self.ib.managedAccounts()[0] if self.ib.managedAccounts() else 'Unknown',
        cash_balance=Decimal(values.get('CashBalance', '0')),
        portfolio_value=Decimal(values.get('NetLiquidation', '0')),
        buying_power=Decimal(values.get('BuyingPower', '0')),
        day_trades_remaining=int(values.get('DayTradesRemaining', '0'))
    )

async def get_portfolio_summary(self) -> Dict:
    """Get portfolio summary"""
    account = await self.get_account()
    positions = await self.get_positions()
    
    invested_value = sum(p.market_value for p in positions)
    
    return {
        'total_value': account.portfolio_value,
        'cash_balance': account.cash_balance,
        'invested_value': invested_value,
        'buying_power': account.buying_power,
        'open_positions': len(positions),
        'day_trades_remaining': account.day_trades_remaining
    }
```

---

### Phase 4: Market Data (Week 4)

#### 4.1 Real-time Data Streaming
```python
# src/brokers/ibkr/market_data.py
from ib_insync import Ticker

class IBKRMarketData:
    def __init__(self, ib: IB):
        self.ib = ib
        self._tickers = {}
    
    async def subscribe(self, symbol: str):
        """Subscribe to real-time data for symbol"""
        contract = Stock(symbol, 'SMART', 'USD')
        contract = await self.ib.qualifyContractsAsync(contract)
        
        if contract:
            ticker = self.ib.reqMktData(contract[0], '', False, False)
            self._tickers[symbol] = ticker
            return ticker
        return None
    
    def get_quote(self, symbol: str) -> Optional[Dict]:
        """Get current quote for symbol"""
        ticker = self._tickers.get(symbol)
        if ticker:
            return {
                'bid': ticker.bid,
                'ask': ticker.ask,
                'last': ticker.last,
                'volume': ticker.volume,
                'high': ticker.high,
                'low': ticker.low,
                'close': ticker.close,
                'time': ticker.time
            }
        return None
    
    def unsubscribe(self, symbol: str):
        """Unsubscribe from symbol"""
        if symbol in self._tickers:
            self.ib.cancelMktData(self._tickers[symbol].contract)
            del self._tickers[symbol]
```

#### 4.2 Historical Data
```python
# src/brokers/ibkr/market_data.py (continued)

async def get_historical_data(
    self,
    symbol: str,
    duration: str = '1 D',
    bar_size: str = '1 min',
    what_to_show: str = 'TRADES'
) -> List[Dict]:
    """Get historical bars"""
    contract = Stock(symbol, 'SMART', 'USD')
    contract = await self.ib.qualifyContractsAsync(contract)
    
    if not contract:
        return []
    
    bars = await self.ib.reqHistoricalDataAsync(
        contract[0],
        endDateTime='',
        durationStr=duration,
        barSizeSetting=bar_size,
        whatToShow=what_to_show,
        useRTH=True  # Regular trading hours only
    )
    
    return [{
        'date': bar.date,
        'open': bar.open,
        'high': bar.high,
        'low': bar.low,
        'close': bar.close,
        'volume': bar.volume
    } for bar in bars]
```

---

### Phase 5: Integration with TradeMind (Week 5)

#### 5.1 Broker Factory
```python
# src/execution/factory.py
from src.brokers.ibkr.client import IBKRBroker
from src.brokers.paper.client import PaperBroker

class BrokerFactory:
    @staticmethod
    def create_broker(broker_type: str, config: dict):
        if broker_type == 'ibkr':
            return IBKRBroker(
                host=config.get('host', '127.0.0.1'),
                port=config.get('port', 7497),
                client_id=config.get('client_id', 1)
            )
        elif broker_type == 'paper':
            return PaperBroker()
        else:
            raise ValueError(f"Unknown broker type: {broker_type}")
```

#### 5.2 Execution Router
```python
# src/execution/router.py
class ExecutionRouter:
    def __init__(self, broker: BaseBroker):
        self.broker = broker
    
    async def execute_signal(self, signal: Dict) -> Dict:
        """Execute trading signal through broker"""
        order = Order(
            symbol=signal['symbol'],
            quantity=signal['quantity'],
            side=signal['side'],
            order_type=signal.get('order_type', 'MARKET'),
            limit_price=signal.get('limit_price'),
            stop_price=signal.get('stop_price')
        )
        
        return await self.broker.place_order(order)
```

#### 5.3 Configuration
```yaml
# config/ibkr_config.yaml
broker:
  type: ibkr  # or 'paper' for testing
  
  ibkr:
    host: 127.0.0.1
    port: 7497  # 7497 = paper trading, 7496 = live
    client_id: 1
    
    # Connection settings
    reconnect_attempts: 5
    reconnect_delay: 5  # seconds
    
    # Trading settings
    default_order_type: MARKET
    time_in_force: DAY
    
    # Safety limits
    max_order_size: 1000  # shares
    max_order_value: 50000  # dollars
    
    # Market data
    market_data_type: 'delayed'  # 'delayed' (free) or 'realtime' (subscription)
```

---

### Phase 6: Testing & Validation (Week 6)

#### 6.1 Unit Tests
```python
# tests/brokers/test_ibkr_client.py
import pytest
from src.brokers.ibkr.client import IBKRBroker

@pytest.fixture
async def broker():
    broker = IBKRBroker(port=7497)  # Paper trading
    await broker.connect()
    yield broker
    await broker.disconnect()

@pytest.mark.asyncio
async def test_connection(broker):
    assert broker._connected is True

@pytest.mark.asyncio
async def test_place_market_order(broker):
    order = Order(
        symbol='AAPL',
        quantity=1,
        side='BUY',
        order_type='MARKET'
    )
    result = await broker.place_order(order)
    assert 'order_id' in result
```

#### 6.2 Integration Tests
- [ ] Connection/disconnection
- [ ] Place and cancel orders
- [ ] Position synchronization
- [ ] Account info retrieval
- [ ] Error handling
- [ ] Reconnection logic

#### 6.3 Paper Trading Validation
- [ ] Run for 1 week on paper account
- [ ] Verify order execution
- [ ] Check position tracking
- [ ] Validate P&L calculations

---

## Risk Management Integration

### Pre-Trade Checks
```python
# src/brokers/ibkr/risk_checks.py

class IBKRRiskManager:
    def __init__(self, broker: IBKRBroker, config: dict):
        self.broker = broker
        self.config = config
    
    async def validate_order(self, order: Order) -> Tuple[bool, str]:
        """Validate order before submission"""
        
        # Check max order size
        if order.quantity > self.config['max_order_size']:
            return False, f"Order size {order.quantity} exceeds max {self.config['max_order_size']}"
        
        # Check buying power
        account = await self.broker.get_account()
        order_value = order.quantity * (order.limit_price or await self._get_market_price(order.symbol))
        
        if order_value > account.buying_power:
            return False, f"Insufficient buying power"
        
        # Check day trades (pattern day trading rule)
        if account.day_trades_remaining <= 0:
            return False, "Day trade limit reached"
        
        return True, "OK"
```

---

## Deployment Considerations

### Docker Setup
```dockerfile
# Dockerfile.ibkr
FROM python:3.11-slim

# Install IB Gateway (headless TWS)
RUN apt-get update && apt-get install -y \
    wget \
    xvfb \
    libxtst6 \
    libxi6 \
    libxrender1

# Download and install IB Gateway
RUN wget https://download2.interactivebrokers.com/installers/ibgateway/stable-standalone/ibgateway-stable-standalone-linux-x64.sh \
    && chmod +x ibgateway-stable-standalone-linux-x64.sh

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "-m", "src.main"]
```

### TWS vs IB Gateway
| Feature | TWS | IB Gateway |
|---------|-----|------------|
| GUI | Yes | No |
| Memory | High (~1GB) | Low (~200MB) |
| Use Case | Development | Production |
| Headless | No | Yes |

**Recommendation**: Use IB Gateway for production deployment

---

## Cost Analysis

### IBKR Pricing
| Service | Cost |
|---------|------|
| API Access | Free |
| Stock Trades (IBKR Lite) | $0 |
| Stock Trades (IBKR Pro) | $0.005/share (min $1) |
| Market Data (US Stocks) | Free (delayed) or $4.50/mo (real-time) |
| Options | $0.65/contract |

### Comparison with Alpaca
| Feature | IBKR | Alpaca |
|---------|------|--------|
| Commission | $0 (Lite) / Low (Pro) | $0 |
| Options | ✅ | ❌ |
| Global Markets | ✅ 150+ | ❌ US only |
| API Quality | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Latency | Lower | Higher |
| Account Min | $0 | $0 |

---

## Implementation Checklist

### Week 1: Foundation
- [ ] Install TWS/IB Gateway
- [ ] Create IBKR paper account
- [ ] Configure API settings
- [ ] Add `ib_insync` dependency
- [ ] Create abstract broker interface
- [ ] Implement IBKR connection manager

### Week 2: Order Management
- [ ] Implement order type mapping
- [ ] Implement `place_order()`
- [ ] Implement `cancel_order()`
- [ ] Implement order tracking
- [ ] Add order validation

### Week 3: Portfolio & Account
- [ ] Implement position sync
- [ ] Implement account info retrieval
- [ ] Add portfolio summary
- [ ] Test position accuracy

### Week 4: Market Data
- [ ] Implement real-time streaming
- [ ] Add historical data retrieval
- [ ] Create market data manager
- [ ] Test data quality

### Week 5: TradeMind Integration
- [ ] Create broker factory
- [ ] Update execution router
- [ ] Add configuration
- [ ] Integrate with orchestrator

### Week 6: Testing & Validation
- [ ] Write unit tests
- [ ] Run paper trading for 1 week
- [ ] Validate all functionality
- [ ] Document known issues

### Go-Live Preparation
- [ ] Switch from paper (7497) to live (7496)
- [ ] Set up monitoring
- [ ] Configure alerts
- [ ] Test emergency stop
- [ ] Create runbook

---

## Next Steps

1. **Set up IBKR paper account** at <https://www.interactivebrokers.com>
2. **Download TWS** or **IB Gateway**
3. **Enable API access** in TWS settings
4. **Start Week 1 implementation**

Would you like me to begin implementing the Week 1 foundation code?
