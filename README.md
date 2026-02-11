# TradeMind AI - Trading Agent

An AI-powered autonomous trading system with rule-based strategies (RSI Mean Reversion, MA Crossover) using an event-driven micro-agent architecture.

## What's New

### 🎉 ib_insync Broker Migration Complete (v2.0)

**✅ Migration Status: Complete**

The ib_insync-based broker (`IBKRInsyncBroker`) is now the **default and only** broker implementation.

**Key Improvements:**
- **Performance**: ~40% lower memory footprint, cleaner async integration
- **Reliability**: Built-in circuit breaker and automatic reconnection
- **Architecture**: Native async/await (no threading complexity)
- **Monitoring**: Comprehensive metrics and health tracking
- **Code Simplicity**: Reduced from ~800 lines to ~400 lines

**Old Threaded Broker:** Removed in v2.0 (no longer supported)

**Configuration:** No changes needed - `ib_insync` is already the default

See [docs/MIGRATION_TO_IB_INSYNC.md](docs/MIGRATION_TO_IB_INSYNC.md) for migration details (historical reference).

## Features

- **Rule-Based Strategies**: RSI Mean Reversion and Moving Average Crossover
- **Multi-Agent System**: Technical Analysis + Risk Management + **Sentiment Analysis (NEW)**
- **AI-Powered Sentiment**: ZAI GLM-4.7 model analyzes market sentiment from price/volume data
- **Smart Caching**: Sentiment results cached for 30 minutes to reduce API calls
- **Real-time Market Data**: Yahoo Finance integration with TimescaleDB storage
- **Backtesting Engine**: Backtrader-based with slippage and commission simulation
- **FastAPI Backend**: RESTful API with HTMX dashboard
- **Redis Event Bus**: Pub/sub for agent communication
- **Risk Management**: Position sizing, stop losses, drawdown limits
- **Command Line Interface**: Full CLI for server management, backtesting, and monitoring
- **LangGraph Orchestration**: Advanced multi-agent workflow with debate protocol and human-in-the-loop
- **IB Gateway Integration**: Native async ib_insync broker with circuit breaker (v2.0)

## Architecture

```
┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ Market Data  │  │ Technical    │  │  Sentiment   │  │    Risk      │
│ Ingestion    │──│ Analysis     │──│   Agent      │──│   Agent      │
└──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘
       │                   │                │                │
       ▼                   ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     EVENT BUS (Redis Pub/Sub)                       │
└─────────────────────────────────────────────────────────────────────┘
       │                   │                │                │
       ▼                   ▼                ▼                ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ Portfolio    │  │  Execution   │  │   FastAPI    │  │     CLI      │
│ Manager      │  │   Engine     │  │   + HTMX     │  │  Interface   │
└──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘
                                   │
                                   ▼
                         ┌─────────────────┐
                         │  IBKR Broker     │
                         │  (ib_insync)    │
                         └────────┬─────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │  IB Gateway     │
                         │   (Live/Paper)  │
                         └─────────────────┘
```

## LangGraph Integration (NEW)

TradeMind AI now uses LangGraph for advanced multi-agent orchestration.

### Architecture

```
┌─────────┐    ┌──────────────┐    ┌──────────────────┐
│  START  │───▶│  Fetch Data  │───▶│ Technical Analysis│
└─────────┘    └──────────────┘    └────────┬─────────┘
                                              │
                    ┌───────────────────────┘
                    ▼
          ┌──────────────────────┐
          │ Sentiment Analysis   │
          └────────┬─────────────┘
                   │
                   ▼
          ┌──────────────────────┐
          │  Debate Protocol    │ (if signals conflict)
          └────────┬─────────────┘
                   │
                   ▼
          ┌──────────────────────┐
          │  Risk Assessment    │
          └────────┬─────────────┘
                   │
                   ▼
          ┌──────────────────────┐
          │   Decision Node     │
          └────────┬─────────────┘
                   │
         ┌──────────┴──────────┐
         ▼                      ▼
┌───────────────┐      ┌───────────────┐
│ Human Review  │      │ Auto-Approve  │
│ (low conf)    │      │ (high conf)   │
└───────┬───────┘      └───────┬───────┘
        │                      │
        └──────────┬───────────┘
                   ▼
          ┌──────────────────────┐
          │  Execute Trade      │
          └────────┬─────────────┘
                   │
                   ▼
            ┌────────────┐
            │    END     │
            └────────────┘
```

### Features

- **Multi-Agent Debate**: Bull vs Bear agents debate when signals conflict
- **Human-in-the-Loop**: Automatic interrupts for low-confidence trades
- **Persistence**: Resume workflows from any point
- **Streaming**: Real-time progress updates
- **Observability**: Full LangSmith integration

### Configuration

```bash
# Enable LangSmith tracing
export LANGSMITH_TRACING=true
export LANGSMITH_API_KEY=your-key
export LANGSMITH_PROJECT=trademind-ai
```

### Usage

```python
from src.trading_graph.graph import create_trading_graph

graph = await create_trading_graph()

result = await graph.ainvoke({
    "symbol": "AAPL",
    "timeframe": "1d"
}, {"thread_id": "workflow-001"})
```

### LangGraph API Endpoints

- `POST /api/langgraph/analyze` - Run full workflow
- `POST /api/langgraph/approve` - Approve interrupted workflow
- `WS /ws/trades/{symbol}` - Real-time trade notifications

See `docs/LANGGRAPH_MIGRATION_GUIDE.md` for complete documentation.

## IB Gateway Integration

TradeMind AI provides full integration with Interactive Brokers Gateway for live and paper trading using the native async **ib_insync** library.

### Architecture Overview

```
FastAPI (Async) ─────────────────────────────────────────────┐
      │                                                       │
      │ async/await (native)                                 │
      ▼                                                       │
┌──────────────────────┐        ┌──────────────────────┐      │
│  IBKRInsyncBroker    │────────│  Circuit Breaker     │──────┤
│    (ib_insync)       │        │  + Auto-Reconnect    │      │
│                      │        └──────────────────────┘      │
├──────────────────────┤                                    ┌──┴───┐
│ - place_order()      │        ┌──────────────────────┐    │ Async │
│ - get_account()      │◀───────│  ib_insync IB()      │────┤ Call  │
│ - get_positions()    │        │  (Native Async)      │    │      │
│ - cancel_order()     │        └──────────┬───────────┘    └──────┘
└──────────────────────┘                   │
                                           │ IB API Calls (Async)
                                           ▼
                                 ┌──────────────────────┐
                                 │   IB Gateway         │
                                 │   (127.0.0.1:7497)   │
                                 └───────────────────────┘
```

### IBKR Broker Architecture

#### IBKRInsyncBroker (v2.0 - Default & Only)

TradeMind uses the native async **ib_insync** broker implementation:

- **File**: `src/brokers/ibkr/ibkr_insync_broker.py`
- **Library**: `ib_insync` (async wrapper around IB API)
- **Key Features**:
  - Native async/await code (no threading complexity)
  - Built-in circuit breaker for resilience
  - Auto-reconnection with exponential backoff
  - Lower memory footprint (~40% reduction vs threaded broker)
  - Comprehensive metrics and health tracking
  - Clean FastAPI integration

**Old Threaded Broker:** Removed in v2.0 (no longer supported)

### Key Components

#### 1. IBKRInsyncBroker (`src/brokers/ibkr/ibkr_insync_broker.py`)

- **IBKRInsyncBroker**: Native async broker using `ib_insync`
- **CircuitBreaker**: Automatic protection against connection storms
- **AutoReconnect**: Configurable retry logic with exponential backoff
- **BrokerMetrics**: Request tracking and performance monitoring
- **Lazy Connection**: Connects on first use, not during startup

#### 2. Integration Layer (`src/brokers/ibkr/integration.py`)

- **IBKRIntegration**: Singleton pattern for global IBKR access
- **Broker Selection**: Always uses IBKRInsyncBroker
- **Lazy Connection**: Connects only when needed
- **Portfolio Synchronization**: Syncs with database automatically

#### 3. Base Interface (`src/brokers/base.py`)

- **BaseBroker**: Common interface for all broker implementations
- Ensures consistent API across different brokers

### Configuration

#### Environment Variables

```bash
# Enable IBKR integration
IBKR_ENABLED=true

# Connection settings
IBKR_HOST=127.0.0.1
IBKR_PORT=7497        # 7497=paper, 7496=live
IBKR_CLIENT_ID=1
IBKR_ACCOUNT=U1234567

# Trading mode
IBKR_PAPER_TRADING=true  # true for paper, false for live

# Insync broker settings
IBKR_INSYNC_RECONNECT_ENABLED=true
IBKR_INSYNC_MAX_RECONNECT_ATTEMPTS=5
IBKR_INSYNC_RECONNECT_BACKOFF=5
IBKR_INSYNC_CONNECT_TIMEOUT=10
IBKR_INSYNC_LAZY_CONNECT=true

# Circuit breaker settings
IBKR_CIRCUIT_BREAKER_ENABLED=true
IBKR_CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
IBKR_CIRCUIT_BREAKER_COOLDOWN_SECONDS=60

# Order settings
IBKR_ORDER_TIMEOUT=30
IBKR_RETRY_ATTEMPTS=3
IBKR_RETRY_DELAY_SECONDS=1

# Risk limits
IBKR_MAX_ORDER_VALUE=10000.0
IBKR_MAX_DAILY_ORDERS=100
IBKR_POSITION_SIZE_LIMIT_PCT=0.10

# Market data
IBKR_ENABLE_MARKET_DATA=true
IBKR_SNAPSHOT_DATA=false
IBKR_REAL_TIME_BARS=false
IBKR_DELAYED_DATA=true
```

#### YAML Configuration (`config/ibkr_config.yaml`)

```yaml
ibkr:
  enabled: true
  host: "127.0.0.1"
  port: 7497
  client_id: 1
  paper_trading: true

order:
  timeout_seconds: 30
  retry_attempts: 3

risk:
  max_order_value: 50000
  max_daily_orders: 100
  position_size_limit_pct: 0.10

market_data:
  enable: true
  snapshot_data: false
  delayed_data: true
```

### Setup Instructions

#### 1. Install Dependencies

The ib_insync library is required:

```bash
# Install ib_insync
pip install ib_insync

# Or install all requirements
pip install -r requirements.txt
```

**Note:** The old `ibapi` library is no longer required and has been removed from dependencies.

#### 2. Install IB Gateway

Download IB Gateway from Interactive Brokers:
- macOS/Linux: `~/ibgateway/`
- Windows: `C:\Jts\`

#### 3. Configure IB Gateway

**First-time setup:**
1. Start IB Gateway and login with IBKR credentials
2. Select **Paper Trading** account (recommended for testing)
3. Enable API (Edit → Global Configuration → API → Settings):
   - ✅ Enable ActiveX and Socket Clients
   - Port: `7497` (paper), `7496` (live)
   - Uncheck "Read-Only API" to allow trading
4. Click OK and restart IB Gateway

#### 4. Verify Connection

```bash
# Quick test using ib_insync
python3 -c "
from ib_insync import IB
ib = IB()
ib.connect('127.0.0.1', 7497, clientId=1)
print('✓ Connected to IB Gateway!')
print('Account:', ib.managedAccounts())
ib.disconnect()
"
```

#### 5. Enable IBKR in TradeMind

```bash
# Set environment variables
export IBKR_ENABLED=true
export IBKR_PORT=7497  # Paper trading
export IBKR_PAPER_TRADING=true
```

Or edit `.env`:
```bash
IBKR_ENABLED=true
IBKR_HOST=127.0.0.1
IBKR_PORT=7497
IBKR_PAPER_TRADING=true
```

### API Endpoints

#### IBKR-Specific Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/ibkr/status` | Check IBKR connection status |
| POST | `/api/ibkr/connect` | Connect to IBKR Gateway |
| POST | `/api/ibkr/disconnect` | Disconnect from IBKR |
| GET | `/api/ibkr/account` | Get account summary |
| GET | `/api/ibkr/positions` | Get current positions |
| GET | `/api/ibkr/orders` | Get open orders |
| GET | `/api/ibkr/metrics` | Get broker metrics |
| POST | `/api/ibkr/sync` | Sync portfolio with IBKR |

**Response example:**
```json
{
  "enabled": true,
  "connected": true,
  "paper_trading": true,
  "broker_type": "ib_insync",
  "mode": "paper",
  "metrics": {
    "total_requests": 150,
    "success_rate": 0.993,
    "avg_latency_ms": 245.5,
    "circuit_breaker_trips": 0,
    "reconnection_attempts": 1
  }
}
```

#### Example Usage

```bash
# Check connection status
curl http://localhost:8000/api/ibkr/status

# Get account summary
curl http://localhost:8000/api/ibkr/account

# Get positions
curl http://localhost:8000/api/ibkr/positions

# Get broker metrics
curl http://localhost:8000/api/ibkr/metrics

# Sync portfolio with IBKR
curl -X POST http://localhost:8000/api/ibkr/sync
```

### Testing

#### Run Unit Tests (No IB Gateway Required)
```bash
python run_tests.py --type unit
```

#### Run Integration Tests (IB Gateway Required)
```bash
# Start IB Gateway first
~/ibgateway/start_ibgateway.sh

# Run integration tests
python run_tests.py --type integration

# Or use pytest directly
pytest tests/brokers/ -v -m integration
```

#### Available Test Suites

| Test File | Description |
|-----------|-------------|
| `test_ibkr_client.py` | Core IBKR broker functionality |
| `test_ibkr_errors.py` | Error handling and edge cases |
| `test_ibkr_integration.py` | Integration with database |

### Data Flow

#### Account Info Retrieval
```
FastAPI → IBKRInsyncBroker.get_account()
       → await ib.reqAccountUpdates()
       → ib_insync: async call to IB Gateway
       → Callback: accountSummary()
       → Result extracted → Account data
```

#### Order Placement Flow
```
FastAPI → IBKRInsyncBroker.place_order(order)
       → await ib.placeOrder(order, trade)
       → ib_insync: async call to IB Gateway
       → Callback: openOrder(), orderStatus()
       → Returns order_id
```

### Security Considerations

- **Credentials**: Store IBKR credentials in `.env` (never commit)
- **Paper Trading**: Always use paper trading for testing (port 7497)
- **Order Validation**: All orders validated before submission
- **Position Limits**: Configurable max position size and daily order limits
- **Circuit Breaker**: Automatic halt on excessive connection failures
- **Risk Limits**: Enforced position size and daily order limits

### Troubleshooting

#### Connection Issues

```bash
# Check if IB Gateway is running
ps aux | grep ibgateway

# Verify port is listening
netstat -an | grep 7497

# Test connection manually
python3 -c "
from ib_insync import IB
ib = IB()
ib.connect('127.0.0.1', 7497, clientId=999)
print('Connected!')
ib.disconnect()
"
```

#### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| "Connection refused" | IB Gateway not running | Start IB Gateway |
| "Invalid client ID" | Client ID already in use | Use unique client_id |
| "Not connected" | Connection not established | Call `await connect()` first |
| "Request timed out" | Slow IB Gateway response | Increase timeout |
| "Circuit breaker open" | Too many failures | Wait for cooldown |
| "Insufficient buying power" | Account has no funds | Check account balance |

**See `SYSTEM_DESIGN.md` for detailed architecture documentation.**

## Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Interactive Brokers account (for live trading)
- ZAI API key (for sentiment analysis)

### 1. Clone & Setup

```bash
cd ~/projects/trading-agent

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies (includes ib_insync)
pip install -r requirements.txt
```

### 2. Start Infrastructure

```bash
# Start TimescaleDB and Redis
docker compose up -d

# Verify containers are running
docker compose ps
```

### 3. Initialize Database

```bash
python init_db.py
```

### 4. Setup IB Gateway (For Live/Paper Trading)

IB Gateway connects to Interactive Brokers for algorithmic trading.

```bash
# Start IB Gateway (installed at ~/ibgateway/)
~/ibgateway/start_ibgateway.sh
```

**First-time setup:**
1. **Login** with your IBKR credentials
2. **Select** Paper Trading account (recommended for testing)
3. **Enable API** (Edit → Global Configuration → API → Settings):
   - ✅ Enable ActiveX and Socket Clients
   - Port: `7497` (paper trading)
   - Uncheck "Read-Only API" to allow trading
4. **Click OK**

**Verify connection:**
```bash
python3 -c "
from ib_insync import IB
ib = IB()
ib.connect('127.0.0.1', 7497, clientId=1)
print('✓ Connected to IB Gateway!')
print('Account:', ib.managedAccounts())
ib.disconnect()
"
```

### 5. Run Tests

```bash
# Run all tests
python run_tests.py --type all

# Or run specific test suites
python run_tests.py --type unit          # Unit tests (no IBKR needed)
python run_tests.py --type integration   # Requires IB Gateway running
python run_tests.py --type error         # Error handling tests

# Or use pytest directly
pytest tests/brokers/ -v
```

### 6. Configure Environment

```bash
# Copy example config
cp .env.example .env

# Edit with your settings
nano .env
```

**Required settings:**
```bash
# Database
DATABASE_URL=postgresql://trading:trading123@localhost:5433/trading_agent

# Redis
REDIS_URL=redis://localhost:6379/0

# IBKR (for live trading)
IBKR_HOST=127.0.0.1
IBKR_PORT=7497        # 7497=paper, 7496=live
IBKR_CLIENT_ID=1

# ZAI API (for sentiment analysis)
ZAI_API_KEY=your_key_here

# Trading settings
STARTING_CAPITAL=100000
MAX_POSITION_PCT=0.10
```

### 7. Start the Server

```bash
# Option 1: Use the startup script
./start.sh

# Option 2: Manual start
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

### 8. Access the Application

- **Dashboard**: http://localhost:8000/
- **Backtest Page**: http://localhost:8000/backtest
- **API Health**: http://localhost:8000/health
- **API Docs**: http://localhost:8000/docs

### Quick Commands Cheat Sheet

```bash
# Start everything
docker compose up -d
~/ibgateway/start_ibgateway.sh &
./start.sh

# Check status
docker compose ps
trademind server status

# Run tests
python run_tests.py --type all

# View logs
trademind server logs --follow
docker compose logs -f

# Stop everything
Ctrl+C (to stop server)
docker compose down
```

## API Endpoints

### Portfolio
- `GET /api/portfolio/` - Get portfolio summary
- `GET /api/portfolio/holdings` - Get current holdings
- `POST /api/portfolio/update-prices` - Update prices
- `GET /api/portfolio/performance?days=30` - Get performance history

### Trades
- `GET /api/trades/?limit=50` - Get trade history
- `POST /api/trades/` - Execute manual trade

### Strategies
- `GET /api/strategies/` - List available strategies
- `POST /api/strategies/signal?symbol=AAPL&strategy=rsi` - Get signal
- `POST /api/strategies/backtest` - Run backtest

### Agent
- `GET /api/agent/decisions` - Get agent decision history
- `POST /api/agent/analyze/{symbol}` - Run agent analysis on single symbol
- `POST /api/agent/analyze-batch` - **BATCH ANALYSIS (DEFAULT)** - Analyze multiple stocks concurrently (7x faster)

## Batch Analysis (NEW - Recommended)

The **batch analysis endpoint** is the fastest way to analyze multiple stocks:

### API Usage
```bash
# Analyze multiple stocks in one call (3 seconds for 11 stocks)
curl -X POST http://localhost:8000/api/agent/analyze-batch \
  -H "Content-Type: application/json" \
  -d '{"symbols": ["AAPL", "TSLA", "NVDA", "AMZN", "GOOGL"]}'
```

### CLI Usage
```bash
# Analyze entire watchlist
trademind config analyze --watchlist

# Analyze specific stocks
trademind config analyze AAPL TSLA NVDA

# Output example:
# ✓ Analyzed 11/11 stocks
#   Time: ~3 seconds (vs 22s sequential)
#
# 🟢 AAPL   @ $182.50 → BUY   (conf: 75%)
# ⚪ TSLA   @ $245.30 → HOLD  (conf: 45%)
# 🔴 NVDA   @ $875.20 → SELL  (conf: 60%)
```

### Performance
- **Sequential**: ~22 seconds for 11 stocks
- **Batch**: ~3 seconds for 11 stocks
- **Speedup**: 7x faster
- **Cost**: Same (concurrent processing, not parallel LLM calls)

## Command Line Interface (NEW)

Full CLI for managing the trading agent without the web dashboard:

```bash
# Server management
trademind server start
trademind server stop
trademind server status
trademind server logs --follow

# Portfolio
trademind portfolio              # View summary
trademind portfolio holdings     # Detailed holdings
trademind portfolio performance  # Performance metrics

# Trades
trademind trades list --limit 20
trademind trades today

# Strategies
trademind strategies list
trademind strategies performance

# Backtesting
trademind backtest run --strategy rsi --symbol AAPL --days 90

# Safety
trademind safety status
trademind safety emergency-stop
```

See `CLI_PLAN.md` for complete documentation.

## Strategies

### RSI Mean Reversion
- **Buy**: When RSI < 30 (oversold)
- **Sell**: When RSI > 70 (overbought)
- **Parameters**: period=14, oversold=30, overbought=70

### MA Crossover
- **Buy**: Golden Cross (50 MA crosses above 200 MA)
- **Sell**: Death Cross (50 MA crosses below 200 MA)
- **Parameters**: fast_period=50, slow_period=200

## Sentiment Analysis Agent (NEW)

The sentiment agent uses **ZAI GLM-4.7** to analyze market sentiment from recent price and volume data.

### How It Works
1. Analyzes 5-day price/volume summary
2. Calls ZAI GLM-4.7 API for sentiment classification
3. Returns: bullish / bearish / neutral with confidence score
4. Converts to BUY/SELL/HOLD trading signal
5. Integrated into orchestrator with 30% weight

### Features
- **Smart Caching**: 30-minute TTL cache per symbol to reduce API calls
- **Retry Logic**: Exponential backoff (3 attempts) for API resilience
- **Fallback Mode**: RSI + volume analysis when API unavailable
- **Confidence Scoring**: 0-1 range with validation

### Configuration
```python
# Sentiment source mode
SENTIMENT_SOURCE=auto        # Options: llm, technical, auto

# Enable/disable sentiment agent
SENTIMENT_ENABLED=true

# ZAI API Configuration (only needed for llm mode)
ZAI_API_KEY=your_key_here
ZAI_MODEL=glm-4.7
ZAI_TEMPERATURE=0.3
ZAI_TIMEOUT=30
```

### Sentiment Modes
- **`llm`**: Always use ZAI GLM-4.7 AI model (requires API key, ~$0.0004/analysis)
- **`technical`**: Always use RSI + volume indicators (free, no API needed)
- **`auto`**: Use LLM if API key available, else technical (default)

### CLI Commands
```bash
# View sentiment configuration
trademind config sentiment show

# Set sentiment source
trademind config sentiment set-source llm         # Use AI
trademind config sentiment set-source technical   # Use indicators
trademind config sentiment set-source auto        # Smart fallback

# Quick commands
trademind config sentiment use-llm
trademind config sentiment use-technical
trademind config sentiment use-auto
```

### Example Output
```json
{
  "agent": "sentiment",
  "decision": "HOLD",
  "confidence": 0.65,
  "reasoning": "Sentiment: neutral - Price consolidating with mixed volume signals"
}
```

## Backtesting

Run a backtest via API:

```bash
curl -X POST http://localhost:8000/api/strategies/backtest \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "AAPL",
    "strategy": "rsi",
    "initial_cash": 100000
  }'
```

Results include:
- Total Return
- Sharpe Ratio
- Max Drawdown
- Win Rate
- Number of Trades

## Configuration

Edit `src/config.py` or set environment variables:

```python
# Database (TimescaleDB on port 5433)
DATABASE_URL=postgresql://trading:trading123@localhost:5433/trading_agent

# Redis
REDIS_URL=redis://localhost:6379/0

# Trading
STARTING_CAPITAL=100000
MAX_POSITION_PCT=0.10
STOP_LOSS_PCT=0.05
TAKE_PROFIT_PCT=0.10

# Sentiment Agent (NEW)
SENTIMENT_ENABLED=true
ZAI_API_KEY=your_zai_key_here
ZAI_MODEL=glm-4.7
ZAI_TEMPERATURE=0.3
ZAI_TIMEOUT=30

# Watchlist
WATCHLIST=["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META"]

# IBKR (for live trading)
IBKR_ENABLED=true
IBKR_HOST=127.0.0.1
IBKR_PORT=7497
IBKR_CLIENT_ID=1
IBKR_PAPER_TRADING=true

# ib_insync broker settings
IBKR_INSYNC_RECONNECT_ENABLED=true
IBKR_CIRCUIT_BREAKER_ENABLED=true
```

## Database Schema

### Market Data (TimescaleDB Hypertable)
- `time`, `symbol`, `open`, `high`, `low`, `close`, `volume`

### Trades
- `id`, `timestamp`, `symbol`, `action`, `quantity`, `price`, `strategy`, `reasoning`

### Holdings
- `symbol`, `quantity`, `avg_cost`, `current_price`, `market_value`, `unrealized_pnl`

### Agent Decisions
- `id`, `timestamp`, `symbol`, `agent`, `decision`, `confidence`, `reasoning`

## Project Structure

```
trading-agent/
├── docker-compose.yml          # TimescaleDB + Redis
├── requirements.txt
├── tasks.md                    # Development tasks
├── cli/                        # Command Line Interface (NEW)
│   ├── main.py                 # CLI entry point
│   ├── server.py               # Server commands
│   ├── portfolio.py            # Portfolio commands
│   ├── trades.py               # Trade commands
│   ├── strategies.py           # Strategy commands
│   ├── safety.py               # Safety commands
│   └── backtest.py             # Backtest commands
├── src/
│   ├── main.py                 # FastAPI app
│   ├── config.py               # Settings
│   ├── core/
│   │   ├── database.py         # SQLAlchemy + TimescaleDB
│   │   ├── events.py           # Redis pub/sub
│   │   └── cache.py            # Redis cache
│   ├── data/
│   │   ├── providers.py        # yfinance integration
│   │   ├── ingestion.py        # Data pipeline
│   │   └── indicators.py       # Technical indicators
│   ├── strategies/
│   │   ├── rsi_reversion.py    # RSI strategy
│   │   └── ma_crossover.py     # MA strategy
│   ├── agents/
│   │   ├── technical.py        # TA agent
│   │   ├── risk.py             # Risk agent
│   │   ├── sentiment.py        # Sentiment agent (NEW)
│   │   └── orchestrator.py     # Signal combiner
│   ├── portfolio/
│   │   └── manager.py          # Portfolio tracking
│   ├── backtest/
│   │   └── engine.py           # Backtrader wrapper
│   ├── brokers/
│   │   ├── base.py             # Base broker interface
│   │   └── ibkr/
│   │       ├── integration.py  # IBKR integration layer
│   │       └── ibkr_insync_broker.py  # Native async broker (v2.0)
│   └── api/
│       └── templates/          # HTMX templates
└── tests/
    └── brokers/                # IBKR broker tests
```

## Development

### Running Tests
```bash
pytest tests/
```

### Adding New Strategy
1. Create file in `src/strategies/`
2. Inherit from `BaseStrategy`
3. Implement `generate_signal()` method
4. Register in `TechnicalAgent`

### Adding New Agent
1. Create file in `src/agents/`
2. Inherit from `BaseAgent`
3. Implement `analyze()` method
4. Register in API routes

## License

MIT
