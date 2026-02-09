# TradeMind AI - Trading Agent

An AI-powered autonomous trading system with rule-based strategies (RSI Mean Reversion, MA Crossover) using an event-driven micro-agent architecture.

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

# Install dependencies
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
│   └── api/
│       └── templates/          # HTMX templates
└── tests/
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
