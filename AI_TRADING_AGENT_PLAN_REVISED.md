# AI Trading Agent - Project Plan (Revised)

## Overview

An AI-powered autonomous trading system that simulates stock trading with the goal of maximizing profit. Uses an event-driven micro-agent architecture for scalability and robustness.

**Key Principle**: Start with deterministic rule-based strategies, add AI as an enhancement layer.

---

## Revised Architecture (Event-Driven Micro-Agents)

```
┌─────────────────────────────────────────────────────────────────┐
│                    AI TRADING AGENT                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ Market Data  │  │ Technical    │  │  Sentiment   │         │
│  │ Ingestion    │──│ Analysis     │  │   Agent      │         │
│  │   (Redis)    │  │  (Code)      │  │   (LLM)      │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│         │                   │                 │                │
│         ▼                   ▼                 ▼                │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │              EVENT BUS (Redis Pub/Sub)                   │ │
│  │  MarketDataUpdated → SignalGenerated → RiskChecked      │ │
│  └──────────────────────────────────────────────────────────┘ │
│         │                   │                 │                │
│         ▼                   ▼                 ▼                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │     Risk     │  │  Portfolio   │  │  Execution   │         │
│  │   Agent      │──│   Agent      │──│   Engine     │         │
│  │  (Rules)     │  │              │  │              │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│         │                                                        │
│         ▼                                                        │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              ORCHESTRATOR (Weighted Voting)              │   │
│  │  Combines signals from all agents with confidence        │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              Web Dashboard (FastAPI + HTMX)              │   │
│  │  Portfolio Overview • Trade History • Backtesting       │   │
│  │  Performance Charts • Agent Activity • Strategy Config   │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Revised Technology Stack

| Component | Technology | Notes |
|-----------|------------|-------|
| **Backend** | Python 3.11, FastAPI | Core API |
| **Task Queue** | RQ (Redis Queue) | Simpler than Celery |
| **Database** | PostgreSQL + TimescaleDB | Trades + time-series market data |
| **Cache/Events** | Redis | Pub/sub for events, caching |
| **Market Data** | yfinance + Backtrader | Backtrader for backtesting |
| **Indicators** | pandas-ta or TA-Lib | Technical analysis |
| **AI/LLM** | OpenAI GPT-4/Claude | Strategy selection, sentiment |
| **Frontend** | HTMX + Alpine.js + Tailwind | Simpler than React |
| **Charts** | Plotly or Chart.js | Performance visualization |
| **Testing** | Pytest | Unit + integration tests |

---

## Micro-Agent Design

### 1. Technical Analysis Agent (Pure Code)
```python
class TechnicalAgent:
    """Calculates technical indicators, no LLM"""
    
    def analyze(self, symbol: str, data: pd.DataFrame) -> Signal:
        # RSI, MACD, Moving Averages, Bollinger Bands
        # Returns: BUY/SELL/HOLD with confidence
        pass
```

### 2. Sentiment Agent (LLM-Powered)
```python
class SentimentAgent:
    """Analyzes news and social media sentiment"""
    
    def analyze(self, symbol: str, news: List[str]) -> Signal:
        # Uses GPT to analyze sentiment from news
        # Returns: BULLISH/BEARISH/NEUTRAL
        pass
```

### 3. Risk Agent (Rule-Based)
```python
class RiskAgent:
    """Validates trades against risk rules"""
    
    def validate(self, trade: Trade, portfolio: Portfolio) -> bool:
        # Position sizing, stop losses, drawdown limits
        # Returns: True if trade passes risk checks
        pass
```

### 4. Portfolio Agent
```python
class PortfolioAgent:
    """Manages allocations and rebalancing"""
    
    def rebalance(self, target_allocations: Dict) -> List[Trade]:
        # Kelly Criterion, correlation checks
        pass
```

### 5. Orchestrator
```python
class Orchestrator:
    """Combines agent signals with weighted voting"""
    
    def decide(self, signals: List[Signal]) -> FinalDecision:
        # Weight: Technical 40%, Sentiment 30%, Risk 30%
        # Override: Risk agent can veto
        pass
```

---

## Revised Implementation Phases

### Phase 1: Foundation (Week 1) - STARTING NOW
**Focus**: Data pipeline, technical indicators, basic backtesting

- [ ] Project structure with proper separation
- [ ] TimescaleDB setup for time-series data
- [ ] yfinance integration with caching
- [ ] Technical indicator library (pandas-ta)
- [ ] Event bus with Redis Pub/Sub
- [ ] Basic portfolio tracker (in-memory → DB)
- [ ] Rule-based strategy: RSI Mean Reversion
- [ ] Rule-based strategy: Moving Average Crossover

**Deliverable**: Can fetch data, calculate indicators, run backtests

### Phase 2: Strategy Engine (Week 2)
**Focus**: Multiple strategies, realistic backtesting, paper trading

- [ ] Backtrader integration for backtesting
- [ ] 3+ rule-based strategies with parameters
- [ ] Realistic backtesting (slippage, latency simulation)
- [ ] Walk-forward analysis
- [ ] Paper trading execution engine
- [ ] Trade logging with reasoning
- [ ] Performance metrics (Sharpe, max drawdown, win rate)

**Deliverable**: Backtest shows realistic results, paper trading active

### Phase 3: AI Integration (Week 3)
**Focus**: LLM for strategy selection and sentiment

- [ ] Sentiment agent with news analysis
- [ ] Strategy selection agent (chooses which rule-based strategy to use)
- [ ] Meta-strategy: Combine multiple rule-based signals
- [ ] Agent reasoning logging and explainability
- [ ] A/B testing: Compare rule-based vs AI-hybrid

**Deliverable**: AI enhances but doesn't replace rule-based strategies

### Phase 4: Dashboard & Polish (Week 4)
**Focus**: Web UI, real-time updates, deployment

- [ ] FastAPI + HTMX dashboard
- [ ] Real-time portfolio updates (WebSocket or SSE)
- [ ] Performance charts with Plotly
- [ ] Strategy configuration UI
- [ ] Agent activity monitor
- [ ] Docker + deployment

**Deliverable**: Full web application, deployed and running

---

## Database Schema (TimescaleDB)

```sql
-- Market data (TimescaleDB hypertable)
CREATE TABLE market_data (
    time TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    open DECIMAL(12, 4),
    high DECIMAL(12, 4),
    low DECIMAL(12, 4),
    close DECIMAL(12, 4),
    volume BIGINT,
    PRIMARY KEY (time, symbol)
);
SELECT create_hypertable('market_data', 'time');

-- Technical indicators (materialized view or computed)
CREATE TABLE indicators (
    time TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    rsi DECIMAL(5, 2),
    macd DECIMAL(10, 4),
    macd_signal DECIMAL(10, 4),
    ma_50 DECIMAL(12, 4),
    ma_200 DECIMAL(12, 4),
    bb_upper DECIMAL(12, 4),
    bb_lower DECIMAL(12, 4),
    PRIMARY KEY (time, symbol)
);
SELECT create_hypertable('indicators', 'time');

-- Trades
CREATE TABLE trades (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    symbol TEXT NOT NULL,
    action TEXT NOT NULL, -- BUY, SELL
    quantity INTEGER NOT NULL,
    price DECIMAL(12, 4) NOT NULL,
    total_value DECIMAL(15, 2) NOT NULL,
    strategy TEXT NOT NULL,
    reasoning TEXT,
    confidence DECIMAL(3, 2),
    agent_signals JSONB -- Store all agent signals
);

-- Portfolio snapshots
CREATE TABLE portfolio_snapshots (
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    total_value DECIMAL(15, 2),
    cash_balance DECIMAL(15, 2),
    invested_value DECIMAL(15, 2),
    daily_pnl DECIMAL(15, 2),
    total_return_pct DECIMAL(8, 4)
);

-- Holdings (current positions)
CREATE TABLE holdings (
    symbol TEXT PRIMARY KEY,
    quantity INTEGER NOT NULL,
    avg_cost DECIMAL(12, 4),
    current_price DECIMAL(12, 4),
    market_value DECIMAL(15, 2),
    unrealized_pnl DECIMAL(15, 2),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Agent decisions log
CREATE TABLE agent_decisions (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    symbol TEXT NOT NULL,
    agent TEXT NOT NULL, -- technical, sentiment, risk, orchestrator
    decision TEXT NOT NULL,
    confidence DECIMAL(3, 2),
    data JSONB, -- Agent-specific data
    reasoning TEXT
);
```

---

## Key Design Decisions (From OpenCode Review)

### 1. Start with Rule-Based Strategies
- **Why**: Prove the system works before adding AI complexity
- **First strategies**: RSI Mean Reversion, MA Crossover
- **AI comes later**: Strategy selection, sentiment analysis

### 2. TimescaleDB for Market Data
- **Why**: Optimized for time-series, better compression
- **Alternative**: InfluxDB (but TimescaleDB is PostgreSQL-compatible)
- **Benefit**: Single database for trades AND market data

### 3. Event-Driven Architecture
- **Why**: Better scalability, fault isolation
- **Implementation**: Redis Pub/Sub
- **Events**: MarketDataUpdated → AnalysisTriggered → SignalGenerated → RiskChecked → OrderExecuted

### 4. HTMX Instead of React
- **Why**: Faster development, less complexity
- **Best for**: FastAPI backend with server-side rendering
- **Trade-off**: Less interactive than React

### 5. Backtrader for Backtesting
- **Why**: Battle-tested, built-in indicators
- **Alternative**: Zipline (more complex)
- **Benefit**: Realistic simulation with slippage, commission

---

## Risk Management (Critical)

```python
RISK_RULES = {
    "max_position_pct": 0.10,      # 10% per stock
    "max_sector_pct": 0.30,        # 30% per sector
    "stop_loss_pct": 0.05,         # 5% stop loss
    "take_profit_pct": 0.10,       # 10% take profit
    "max_daily_loss_pct": 0.03,    # Stop trading after 3% loss
    "min_cash_pct": 0.10,          # Keep 10% cash
    "max_correlation": 0.70,       # Don't hold correlated stocks
    "position_sizing": "kelly",     # Kelly Criterion
}
```

---

## Configuration

```yaml
# config.yaml
app:
  name: "TradeMind AI"  # or whatever name you choose
  mode: "paper"
  timezone: "America/New_York"

database:
  url: "postgresql://user:pass@localhost:5432/trading_agent"
  
redis:
  url: "redis://localhost:6379/0"

trading:
  starting_capital: 100000.00
  max_position_pct: 0.10
  max_daily_loss_pct: 0.03
  stop_loss_pct: 0.05
  take_profit_pct: 0.10
  check_interval_minutes: 15
  trading_hours:
    start: "09:30"
    end: "16:00"
    
data:
  provider: "yahoo"
  cache_duration_minutes: 5
  
agents:
  technical:
    weight: 0.40
    enabled: true
  sentiment:
    weight: 0.30
    enabled: false  # Enable in Phase 3
    llm_model: "gpt-3.5-turbo"  # Cheaper for sentiment
  risk:
    weight: 0.30
    enabled: true
    can_veto: true  # Risk agent can override others

strategies:
  rsi_mean_reversion:
    enabled: true
    rsi_period: 14
    oversold: 30
    overbought: 70
  ma_crossover:
    enabled: true
    fast_period: 50
    slow_period: 200

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

## Project Structure

```
trading-agent/
├── README.md
├── requirements.txt
├── docker-compose.yml
├── config.yaml
├── alembic/                    # Database migrations
├── src/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app
│   ├── config.py               # Configuration loader
│   ├── core/
│   │   ├── __init__.py
│   │   ├── events.py           # Event bus (Redis)
│   │   ├── database.py         # DB connection
│   │   └── cache.py            # Redis cache
│   ├── data/
│   │   ├── __init__.py
│   │   ├── providers.py        # yfinance integration
│   │   ├── ingestion.py        # Continuous data fetch
│   │   └── indicators.py       # Technical indicators
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base.py             # Base agent class
│   │   ├── technical.py        # Technical analysis agent
│   │   ├── sentiment.py        # Sentiment agent (LLM)
│   │   ├── risk.py             # Risk management agent
│   │   ├── portfolio.py        # Portfolio agent
│   │   └── orchestrator.py     # Signal combiner
│   ├── strategies/
│   │   ├── __init__.py
│   │   ├── base.py             # Base strategy class
│   │   ├── rsi_reversion.py    # RSI mean reversion
│   │   └── ma_crossover.py     # Moving average crossover
│   ├── execution/
│   │   ├── __init__.py
│   │   ├── paper.py            # Paper trading broker
│   │   └── risk_manager.py     # Risk validation
│   ├── portfolio/
│   │   ├── __init__.py
│   │   ├── manager.py          # Portfolio state
│   │   └── analytics.py        # Performance metrics
│   ├── backtest/
│   │   ├── __init__.py
│   │   ├── engine.py           # Backtesting engine
│   │   └── metrics.py          # Performance calculations
│   └── api/
│       ├── __init__.py
│       ├── routes/
│       │   ├── __init__.py
│       │   ├── portfolio.py
│       │   ├── trades.py
│       │   ├── strategies.py
│       │   └── agent.py
│       └── templates/          # HTMX templates
│           ├── base.html
│           ├── dashboard.html
│           └── backtest.html
├── tests/
│   ├── __init__.py
│   ├── test_indicators.py
│   ├── test_strategies.py
│   └── test_portfolio.py
└── notebooks/                  # Analysis notebooks
    └── strategy_analysis.ipynb
```

---

## Next Steps (Starting Phase 1)

1. ✅ Project folder created: `~/projects/trading-agent/`
2. 🔄 Set up Python environment (venv + dependencies)
3. 🔄 Initialize database (TimescaleDB via Docker)
4. 🔄 Create project structure
5. 🔄 Build market data ingestion pipeline
6. 🔄 Implement first strategy (RSI Mean Reversion)

**Ready to start?** I can begin setting up the environment now.
