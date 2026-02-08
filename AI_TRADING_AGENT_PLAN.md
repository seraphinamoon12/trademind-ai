# AI Trading Agent - Project Plan

## Overview

An AI-powered autonomous trading system that simulates stock trading with the goal of maximizing profit. The system uses AI agents to analyze market data, make trading decisions, and manage risk.

---

## Core Architecture

### 1. System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    AI TRADING AGENT                         │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Market     │  │   Trading    │  │  Portfolio   │      │
│  │   Data       │──│   Agent      │──│  Manager     │      │
│  │   Provider   │  │   (AI Brain) │  │              │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│         │                   │                 │             │
│         ▼                   ▼                 ▼             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Strategy   │  │    Risk      │  │   Execution  │      │
│  │   Engine     │  │   Manager    │  │   Engine     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Web Dashboard (FastAPI)                │   │
│  │  • Portfolio Overview  • Trade History             │   │
│  │  • Performance Charts  • Agent Logs                │   │
│  │  • Strategy Config     • Real-time Updates         │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## Technology Stack

| Component | Technology |
|-----------|------------|
| **Backend** | Python 3.11, FastAPI |
| **AI/Agent Framework** | LangChain, LangGraph |
| **LLM** | OpenAI GPT-4 / Claude (for strategy reasoning) |
| **Market Data** | Yahoo Finance (yfinance), Alpha Vantage |
| **Database** | PostgreSQL (trades, portfolio history) |
| **Cache** | Redis (market data, session state) |
| **Frontend** | React or HTMX + Tailwind CSS |
| **Task Queue** | Celery + Redis (background trading) |
| **Monitoring** | Prometheus + Grafana (optional) |

---

## Key Features

### 1. AI Trading Agent

**Capabilities:**
- Technical analysis (RSI, MACD, Moving Averages, Bollinger Bands)
- Fundamental analysis (P/E ratios, earnings, news sentiment)
- Pattern recognition (chart patterns, trend detection)
- Risk-aware decision making
- Portfolio rebalancing

**Agent Workflow:**
```
1. FETCH market data (prices, volume, indicators)
2. ANALYZE using technical/fundamental strategies
3. DECIDE (buy/sell/hold) with confidence score
4. VALIDATE against risk management rules
5. EXECUTE trade (paper trading)
6. LOG decision reasoning and outcome
7. LEARN from results (feedback loop)
```

### 2. Trading Strategies

**Built-in Strategies:**
- **Momentum Trading**: Buy rising stocks, sell falling ones
- **Mean Reversion**: Buy oversold, sell overbought (RSI-based)
- **Trend Following**: Follow MACD and moving average crossovers
- **Breakout Trading**: Buy on resistance breakout
- **AI-Hybrid**: LLM analyzes news sentiment + technical indicators

**Custom Strategy Builder:**
- Visual strategy editor
- Combine multiple indicators
- Backtesting framework
- Strategy performance comparison

### 3. Risk Management

**Rules:**
- Max position size (e.g., 10% of portfolio per stock)
- Stop-loss orders (e.g., -5% from entry)
- Take-profit targets (e.g., +10% from entry)
- Daily loss limits (e.g., stop trading after -3% day)
- Diversification requirements (min 5 sectors)
- Volatility filters (avoid high-volatility stocks)

### 4. Market Data Integration

**Data Sources:**
```python
# Primary: Yahoo Finance (free, real-time)
- Stock prices (1min, 5min, 15min, 1h, daily)
- Historical data for backtesting
- Company fundamentals

# Secondary: Alpha Vantage (API key required)
- Technical indicators
- News sentiment
- Economic data

# Tertiary: Web scraping (optional)
- Reddit sentiment (r/wallstreetbets)
- Twitter sentiment
- News headlines
```

### 5. Portfolio Management

**Features:**
- Starting capital: $100,000 (simulated)
- Real-time P&L tracking
- Position sizing
- Cash management
- Transaction history
- Tax-loss harvesting (simulated)

### 6. Dashboard

**Views:**
- **Overview**: Current portfolio value, daily P&L, total return
- **Holdings**: Active positions, avg cost, current price, unrealized P&L
- **Trade History**: All executed trades with reasoning
- **Performance**: Charts (cumulative returns, drawdowns, win rate)
- **Agent Activity**: Live agent decisions and thought process
- **Strategy Config**: Adjust parameters, enable/disable strategies
- **Watchlist**: Track stocks the agent is monitoring

---

## Database Schema

```sql
-- Portfolio snapshot
CREATE TABLE portfolio_snapshots (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT NOW(),
    total_value DECIMAL(15, 2),
    cash_balance DECIMAL(15, 2),
    invested_value DECIMAL(15, 2),
    daily_pnl DECIMAL(15, 2),
    total_return_pct DECIMAL(8, 4)
);

-- Holdings
CREATE TABLE holdings (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    quantity INTEGER NOT NULL,
    avg_cost DECIMAL(12, 4),
    current_price DECIMAL(12, 4),
    market_value DECIMAL(15, 2),
    unrealized_pnl DECIMAL(15, 2),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Trades
CREATE TABLE trades (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    action VARCHAR(4) NOT NULL, -- BUY or SELL
    quantity INTEGER NOT NULL,
    price DECIMAL(12, 4) NOT NULL,
    total_value DECIMAL(15, 2) NOT NULL,
    timestamp TIMESTAMP DEFAULT NOW(),
    strategy VARCHAR(50), -- which strategy triggered
    reasoning TEXT, -- AI agent reasoning
    confidence_score DECIMAL(3, 2) -- 0.0 to 1.0
);

-- Agent decisions log
CREATE TABLE agent_decisions (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT NOW(),
    symbol VARCHAR(10) NOT NULL,
    decision VARCHAR(4) NOT NULL, -- BUY, SELL, HOLD
    confidence DECIMAL(3, 2),
    technical_signals JSONB,
    fundamental_signals JSONB,
    news_sentiment JSONB,
    final_reasoning TEXT
);

-- Market data cache
CREATE TABLE market_data (
    symbol VARCHAR(10) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    open DECIMAL(12, 4),
    high DECIMAL(12, 4),
    low DECIMAL(12, 4),
    close DECIMAL(12, 4),
    volume BIGINT,
    PRIMARY KEY (symbol, timestamp)
);
```

---

## API Endpoints

```python
# Portfolio
GET  /api/portfolio              # Current holdings and value
GET  /api/portfolio/history      # Historical portfolio values

# Trading
POST /api/trade/execute          # Manual trade (for testing)
GET  /api/trades                 # Trade history
GET  /api/trades/{id}            # Specific trade details

# Agent
GET  /api/agent/status           # Is agent running?
POST /api/agent/start            # Start trading agent
POST /api/agent/stop             # Stop trading agent
GET  /api/agent/decisions        # Agent decision log
GET  /api/agent/config           # Current strategy config
PUT  /api/agent/config           # Update strategy config

# Market Data
GET  /api/market/quote/{symbol}  # Current price
GET  /api/market/history/{symbol}# Historical prices
GET  /api/market/watchlist       # Stocks being monitored

# Strategies
GET  /api/strategies             # List available strategies
POST /api/strategies/backtest    # Run backtest
GET  /api/strategies/performance # Strategy performance metrics
```

---

## AI Agent Prompt Template

```python
TRADING_AGENT_PROMPT = """
You are an expert AI trading agent. Analyze the following market data and make a trading decision.

PORTFOLIO STATE:
- Cash Available: ${cash}
- Current Holdings: {holdings}
- Total Portfolio Value: ${total_value}

MARKET DATA FOR {symbol}:
- Current Price: ${current_price}
- Daily Change: {daily_change_pct}%
- 52-Week Range: ${low_52w} - ${high_52w}
- Volume: {volume}
- RSI (14): {rsi}
- MACD: {macd}
- 50-day MA: ${ma_50}
- 200-day MA: ${ma_200}

RECENT NEWS SENTIMENT:
{news_sentiment}

TECHNICAL ANALYSIS:
{technical_summary}

RISK CONSTRAINTS:
- Max position size: 10% of portfolio
- Stop loss: -5% from entry
- Daily loss limit: -3% of portfolio

DECISION OPTIONS:
1. BUY (specify quantity and reasoning)
2. SELL (specify quantity and reasoning)
3. HOLD (explain why)

Provide your decision in JSON format:
{
    "decision": "BUY/SELL/HOLD",
    "quantity": <number>,
    "confidence": <0.0-1.0>,
    "reasoning": "<detailed explanation>",
    "risk_assessment": "<risk evaluation>"
}
"""
```

---

## Implementation Phases

### Phase 1: Core Framework (Week 1)
- [ ] Set up FastAPI project structure
- [ ] Database models and migrations
- [ ] Market data provider (yfinance integration)
- [ ] Basic portfolio management
- [ ] Paper trading execution engine

### Phase 2: AI Agent (Week 2)
- [ ] LangChain agent setup
- [ ] Technical indicators calculation
- [ ] Trading strategy implementations
- [ ] Risk management rules
- [ ] Agent decision logging

### Phase 3: Dashboard (Week 3)
- [ ] Portfolio overview page
- [ ] Trade history and analytics
- [ ] Agent activity monitor
- [ ] Strategy configuration UI
- [ ] Real-time updates (WebSocket)

### Phase 4: Advanced Features (Week 4)
- [ ] Backtesting framework
- [ ] Multiple strategy support
- [ ] News sentiment analysis
- [ ] Performance reporting
- [ ] Docker deployment

---

## Configuration

```yaml
# config.yaml
app:
  name: "AI Trading Agent"
  mode: "paper"  # paper or live (not implemented)
  timezone: "America/New_York"

trading:
  starting_capital: 100000.00
  max_position_pct: 0.10  # 10% per stock
  max_daily_loss_pct: 0.03  # Stop trading after 3% loss
  stop_loss_pct: 0.05  # 5% stop loss
  take_profit_pct: 0.10  # 10% take profit
  
agent:
  llm_model: "gpt-4"
  check_interval_minutes: 15
  trading_hours:
    start: "09:30"
    end: "16:00"
  strategies:
    - momentum
    - mean_reversion
    - trend_following
    
data:
  provider: "yahoo"
  cache_duration_minutes: 5
  
watchlist:
  - AAPL
  - GOOGL
  - MSFT
  - AMZN
  - TSLA
  - NVDA
  - META
  - AMD
  - NFLX
  - CRM
```

---

## Risk Disclaimer

⚠️ **IMPORTANT**: This is a simulation/paper trading system only.
- No real money is traded
- For educational and research purposes
- Past performance does not guarantee future results
- AI agents can make mistakes
- Always consult financial advisors for real investments

---

## Next Steps

1. **Review this plan** - Confirm features and scope
2. **Choose project name** - e.g., "TradeMind", "ProfitPilot", "StockAgent"
3. **Select hosting** - Local dev, EC2, or keep it simple with local
4. **Prioritize features** - Which strategies to implement first?
5. **Start development** - Begin Phase 1

**Recommended project location**: `~/projects/trading-agent/`
