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

## Quick Start

### 1. Start the Infrastructure

```bash
cd ~/projects/trading-agent

# Start TimescaleDB and Redis
docker compose up -d

# Verify containers are running
docker compose ps
```

### 2. Initialize Database

```bash
source venv/bin/activate
python init_db.py
```

### 3. Run Tests

```bash
python test_components.py
```

### 4. Start the Server

```bash
# Option 1: Use the startup script
./start.sh

# Option 2: Manual start
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

### 5. Access the Application

- **Dashboard**: http://localhost:8000/
- **Backtest Page**: http://localhost:8000/backtest
- **API Health**: http://localhost:8000/health
- **API Docs**: http://localhost:8000/docs

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
- `POST /api/agent/analyze/{symbol}` - Run agent analysis (includes sentiment)

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
# Enable/disable sentiment agent
SENTIMENT_ENABLED=true

# ZAI API Configuration
ZAI_API_KEY=your_key_here
ZAI_MODEL=glm-4.7
ZAI_TEMPERATURE=0.3
ZAI_TIMEOUT=30
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
