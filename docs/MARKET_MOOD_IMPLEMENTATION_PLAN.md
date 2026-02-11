# Market Mood Detection Feature - Implementation Plan

**Project:** TradeMind AI Trading Agent  
**Feature:** Market Mood Detection  
**Version:** 1.0  
**Date:** February 11, 2026  
**Status:** Planning Phase

---

## Table of Contents
1. [Executive Summary](#executive-summary)
2. [Market Mood Indicators Research](#market-mood-indicators-research)
3. [Architecture Design](#architecture-design)
4. [Implementation Plan](#implementation-plan)
5. [Mood Calculation Algorithm](#mood-calculation-algorithm)
6. [API Design](#api-design)
7. [Cost Analysis](#cost-analysis)
8. [Testing Strategy](#testing-strategy)
9. [Timeline](#timeline)
10. [Risk Mitigation](#risk-mitigation)

---

## Executive Summary

The Market Mood Detection feature will analyze overall market sentiment and provide trading signals based on market psychology indicators. This feature integrates with the existing TradeMind AI system, enhancing the multi-agent workflow with market-wide sentiment context beyond individual stock analysis.

**Key Benefits:**
- Provides market-wide context for individual stock decisions
- Acts as a contrarian indicator for identifying buying/selling opportunities
- Integrates seamlessly with existing LangGraph workflow
- Cost-effective implementation using free data sources

**Technical Approach:**
- Leverage free APIs (Yahoo Finance, public CBOE data)
- Composite mood score combining 5 key indicators
- Integration as a new node in the LangGraph workflow
- Caching to minimize API calls and costs

---

## Market Mood Indicators Research

### 1. VIX (Volatility Index) - The "Fear Gauge"

**Description:** The CBOE Volatility Index measures expected market volatility using a portfolio of options on the S&P 500. It's the market's expectation of 30-day future volatility.

**Data Source Options:**
- **Yahoo Finance (Recommended - Free):** Ticker `^VIX`
  - Daily data with 15-minute delay
  - No API key required
  - Python: `yfinance.download("^VIX")`
  
- **CBOE Website (Free):** https://www.cboe.com/trading/data/vix-delayed-quotes/
  - Delayed data available for download
  - Historical data available in CSV format

- **Alpha Vantage (Free/Paid):** 
  - Free tier: 25 requests/day
  - Paid: $0.005/request after free tier

**Thresholds & Interpretation:**

| VIX Range | Interpretation | Signal |
|-----------|---------------|--------|
| < 20 | Low fear, market stability | Bullish (normal trading) |
| 20-30 | Moderate fear/uncertainty | Neutral (cautious) |
| 30-40 | High fear, increased volatility | Bearish (consider buying) |
| > 40 | Extreme fear, panic | Contrarian BUY opportunity |

**Implementation Notes:**
- Store historical VIX values for trend analysis
- Calculate VIX percent change over 5, 10, 20 days
- Detect VIX spikes (daily change > 20%)
- Weight in composite score: 20%

---

### 2. Market Breadth Indicators

**Description:** Analyzes the number of stocks advancing relative to those declining. Measures market participation in a move.

#### 2a. Advance/Decline Ratio (A/D Ratio)

**Calculation:**
```
A/D Ratio = Number of Advancing Stocks / Number of Declining Stocks
```

**Data Source Options:**
- **Yahoo Finance (Recommended - Free):** 
  - Use `^NYA` (NYSE Composite) or `^NDX` (NASDAQ 100)
  - Extract advance/decline data from metadata
  - Python: Requires parsing from Yahoo Finance pages

- **Investopedia/FactSet (Paid):** Real-time A/D data
  - Subscription required
  - Cost: $50-100/month

- **Manual Calculation (Free):**
  - Download NYSE daily data
  - Count advancers vs decliners
  - Time-consuming but free

**Thresholds & Interpretation:**

| A/D Ratio | Interpretation | Signal |
|-----------|---------------|--------|
| > 1.5 | Strong bullish breadth | Bullish (increase exposure) |
| 1.0-1.5 | Positive breadth | Neutral-Bullish |
| 0.5-1.0 | Mixed breadth | Neutral |
| < 0.5 | Bearish breadth | Bearish (reduce exposure) |

**Implementation Notes:**
- Weight in composite score: 15%
- Calculate 5-day and 20-day moving averages
- Detect breadth divergence (index up, breadth down)

#### 2b. NYSE Advance-Decline Line

**Calculation:**
```
AD Line = Previous AD Line + (Advancing Issues - Declining Issues)
```

**Data Source:** Same as A/D Ratio

**Interpretation:**
- Rising AD Line + Rising Index = Confirmed uptrend
- Falling AD Line + Rising Index = Divergence (bearish warning)
- Falling AD Line + Falling Index = Confirmed downtrend

**Implementation Notes:**
- Use as confirmation signal for market direction
- Weight in composite score: 10%

#### 2c. New Highs-Lows Index

**Calculation:**
```
Highs-Lows % = Stocks at 52-week Highs / (Stocks at Highs + Stocks at Lows) * 100
```

**Data Source:** NYSE/NASDAQ daily market statistics (free)

**Thresholds:**

| Highs-Lows % | Interpretation | Signal |
|--------------|---------------|--------|
| > 70% | Extreme optimism | Contrarian SELL |
| 50-70% | Bullish breadth | Bullish |
| 30-50% | Neutral | Neutral |
| < 30% | Bearish breadth | Bearish |
| < 10% | Extreme pessimism | Contrarian BUY |

**Implementation Notes:**
- Weight in composite score: 10%

---

### 3. Fear & Greed Index

**Description:** CNN's Fear & Greed Index combines 7 indicators into a single 0-100 score.

**Components:**
1. Market Momentum (S&P 500 vs 125-day MA)
2. Stock Price Strength (52-week highs vs lows)
3. Stock Price Breadth (volume in advancing vs declining)
4. Put/Call Ratio
5. Market Volatility (VIX)
6. Safe Haven Demand (bonds vs stocks)
7. Junk Bond Demand

**Data Source Options:**

| Source | Cost | Update Frequency | Access Method |
|--------|------|------------------|---------------|
| **CNN Website** | Free | Daily (4:15 PM ET) | Web scraping (parsing HTML) |
| **Calculate Internally** | Free | Real-time | Implement algorithm using components |
| **Alternative APIs** | Paid | Real-time | Alternative data providers |

**Thresholds & Interpretation:**

| Fear & Greed Score | Classification | Signal |
|---------------------|----------------|--------|
| 0-20 | Extreme Fear | Strong BUY |
| 21-40 | Fear | BUY |
| 41-60 | Neutral | HOLD |
| 61-80 | Greed | SELL/Take Profits |
| 81-100 | Extreme Greed | Strong SELL |

**Implementation Notes:**
- Weight in composite score: 20%
- Implement internal calculation for real-time access
- Cache for 15 minutes to avoid excessive API calls

---

### 4. Put/Call Ratio

**Description:** Measures options market sentiment by comparing put and call volume.

**Calculation:**
```
Put/Call Ratio = Total Put Volume / Total Call Volume
```

**Data Source Options:**
- **CBOE Website (Recommended - Free):** https://www.cboe.com/us/options/market_statistics/daily/
  - Daily CBOE Equity Put/Call Ratio
  - Historical CSV data available
  - No API key required

- **Yahoo Finance (Free):** 
  - Ticker: `^CBOE` (CBOE Put/Call Index)
  - Delayed data
  - Python: `yfinance.download("^CBOE")`

- **OptionsClearingCorp (Free):** 
  - Monthly volume reports
  - Less granular but reliable

**Thresholds & Interpretation:**

| Put/Call Ratio | Interpretation | Signal |
|----------------|---------------|--------|
| < 0.50 | Extreme greed (excessive calls) | Contrarian SELL |
| 0.50-0.70 | Greed | Caution/Take Profits |
| 0.70-1.00 | Neutral | Neutral |
| 1.00-1.50 | Fear | Consider BUY |
| > 1.50 | Extreme fear (excessive puts) | Contrarian BUY |

**Implementation Notes:**
- Weight in composite score: 15%
- Track 5-day moving average for trend
- Detect ratio spikes (daily change > 30%)

---

### 5. Moving Average Trends

**Description:** Analyzes S&P 500 relationship to key moving averages to determine market trend.

**Key Moving Averages:**
- 20-day MA (Short-term trend)
- 50-day MA (Intermediate trend)
- 200-day MA (Long-term trend)

**Data Source:**
- **Yahoo Finance (Free):** Ticker `^GSPC` (S&P 500)
  - Real-time with 15-minute delay
  - Historical data available
  - Python: `yfinance.download("^GSPC")`

**Thresholds & Interpretation:**

| Condition | Interpretation | Signal |
|-----------|---------------|--------|
| Price > 20MA > 50MA > 200MA | Strong uptrend | Bullish |
| Price > 200MA, 50MA crossed above 200MA | Golden Cross | Strong BUY |
| Price < 200MA, 50MA crossed below 200MA | Death Cross | Strong SELL |
| Price < 20MA < 50MA < 200MA | Strong downtrend | Bearish |

**Implementation Notes:**
- Weight in composite score: 10%
- Detect crossovers (golden/death crosses)
- Calculate distance from each MA (%)

---

## Architecture Design

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FastAPI Backend                               │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    API Routes                                  │   │
│  │  GET /api/market/mood       - Current mood snapshot            │   │
│  │  GET /api/market/mood/history - Historical mood data           │   │
│  │  GET /api/market/mood/indicators - Individual indicator values │   │
│  │  GET /api/market/mood/signals - Trading signals               │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                              │                                       │
│                              ▼                                       │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │              MarketMoodDetector (Main Class)                   │   │
│  │  - calculate_mood()                                          │   │
│  │  - get_mood_history()                                        │   │
│  │  - get_trading_signals()                                     │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                              │                                       │
│         ┌────────────────────┼────────────────────┐                  │
│         ▼                    ▼                    ▼                  │
│  ┌──────────────┐    ┌──────────────┐   ┌──────────────┐          │
│  │  Indicators  │    │ Data Providers│   │   Engine     │          │
│  │              │    │              │   │              │          │
│  │ • VIX        │    │ • Yahoo      │   │ • Score Calc │          │
│  │ • Breadth    │    │ • CBOE       │   │ • Trend Det. │          │
│  │ • Fear/Greed │    │ • Alpha Vant.│   │ • Confidence │          │
│  │ • Put/Call   │    │              │   │              │          │
│  │ • MA Trends  │    │              │   │              │          │
│  └──────────────┘    └──────────────┘   └──────────────┘          │
│                              │                                       │
│                              ▼                                       │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                   Data Layer                                   │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │   │
│  │  │ TimescaleDB │  │    Redis    │  │    Cache    │         │   │
│  │  │ (History)   │  │ (Pub/Sub)   │  │ (TTL 15min) │         │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘         │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    LangGraph Integration                              │
│                                                                       │
│  START → fetch_data → technical → sentiment → market_mood → debate   │
│                                             ↑                         │
│                                             │                         │
│                              Market Mood Node (New)                   │
│                              - Get current market mood                │
│                              - Adjust trading signals accordingly     │
└─────────────────────────────────────────────────────────────────────┘
```

### File Structure

```
trading-agent/
├── src/
│   ├── market_mood/                      # NEW: Market Mood Module
│   │   ├── __init__.py                   # Package exports
│   │   ├── detector.py                   # Main MarketMoodDetector class
│   │   ├── models.py                     # Pydantic models for mood data
│   │   ├── engine.py                     # Mood calculation engine
│   │   ├── signals.py                   # Trading signal generator
│   │   │
│   │   ├── indicators/                   # Individual indicator implementations
│   │   │   ├── __init__.py
│   │   │   ├── vix.py                    # VIX indicator fetcher & analyzer
│   │   │   ├── breadth.py                # Market breadth calculator
│   │   │   ├── fear_greed.py             # Fear & Greed calculator
│   │   │   ├── put_call.py               # Put/Call ratio fetcher
│   │   │   └── ma_trend.py               # Moving average trend analyzer
│   │   │
│   │   └── data_providers/               # Data provider implementations
│   │       ├── __init__.py
│   │       ├── yahoo_provider.py         # Yahoo Finance provider
│   │       ├── cboe_provider.py          # CBOE data scraper
│   │       └── base_provider.py          # Base provider class
│   │
│   ├── trading_graph/
│   │   ├── nodes/
│   │   │   ├── __init__.py
│   │   │   ├── data_nodes.py
│   │   │   ├── analysis_nodes.py
│   │   │   ├── execution_nodes.py
│   │   │   └── market_mood_node.py       # NEW: LangGraph node for market mood
│   │   └── ...
│   │
│   ├── api/
│   │   ├── routes/
│   │   │   ├── market_mood.py            # NEW: Market mood API routes
│   │   │   └── ...
│   │   └── ...
│   │
│   └── config.py                          # Add market mood settings
│
├── tests/
│   ├── market_mood/                      # NEW: Market mood tests
│   │   ├── __init__.py
│   │   ├── test_detector.py
│   │   ├── test_indicators/
│   │   │   ├── test_vix.py
│   │   │   ├── test_breadth.py
│   │   │   ├── test_fear_greed.py
│   │   │   ├── test_put_call.py
│   │   │   └── test_ma_trend.py
│   │   └── test_integration.py
│   └── ...
│
├── docs/
│   └── MARKET_MOOD_IMPLEMENTATION_PLAN.md  # This document
│
├── config/
│   └── market_mood_config.yaml             # NEW: Market mood configuration
│
└── requirements.txt                         # Add new dependencies
```

---

## Implementation Plan

### Phase 1: Data Infrastructure (Days 1-3)

**Objective:** Set up data providers and caching layer

**Tasks:**

1. **Create Base Provider Class** (`src/market_mood/data_providers/base_provider.py`)
   - Abstract base for all data providers
   - Common interface: `fetch_data()`, `get_historical_data()`
   - Error handling and retry logic
   - Rate limiting support

2. **Implement Yahoo Finance Provider** (`src/market_mood/data_providers/yahoo_provider.py`)
   - Use `yfinance` library (already in requirements)
   - Fetch VIX, S&P 500, Put/Call ratio data
   - Handle rate limits (5 requests/second)
   - Cache support

3. **Implement CBOE Data Provider** (`src/market_mood/data_providers/cboe_provider.py`)
   - Scrape CBOE website for Put/Call ratio
   - Download historical data CSVs
   - Fallback to cached data if scrape fails

4. **Create Caching Layer** (extend existing `src/core/cache.py`)
   - Redis caching with configurable TTL
   - Cache keys: `mood:{indicator}:{date}`
   - Default TTL: 15 minutes for real-time, 1 hour for historical
   - Invalidation strategy

5. **Create Data Models** (`src/market_mood/models.py`)
   ```python
   class VIXData(BaseModel):
       value: float
       change_pct: float
       timestamp: datetime
       ma5: float
       ma20: float

   class BreadthData(BaseModel):
       ad_ratio: float
       ad_line: float
       new_highs_lows_pct: float
       timestamp: datetime

   class PutCallData(BaseModel):
       ratio: float
       ma5: float
       timestamp: datetime

   class FearGreedData(BaseModel):
       score: int  # 0-100
       classification: str
       components: Dict[str, float]
       timestamp: datetime

   class MATrendData(BaseModel):
       price: float
       ma20: float
       ma50: float
       ma200: float
       golden_cross: bool
       death_cross: bool
       timestamp: datetime

   class MoodScore(BaseModel):
       overall_score: int  # -100 to 100
       classification: str
       confidence: float
       trend: str  # "improving", "declining", "stable"
       indicators: Dict[str, float]
       timestamp: datetime
   ```

**Deliverables:**
- Base provider class
- Yahoo Finance provider
- CBOE provider
- Enhanced caching layer
- Data models

**Acceptance Criteria:**
- All providers implement base interface
- Caching reduces API calls by >80%
- Data models pass validation
- Unit tests pass

---

### Phase 2: Core Indicators (Days 4-7)

**Objective:** Implement all 5 market mood indicators

**Tasks:**

1. **VIX Indicator** (`src/market_mood/indicators/vix.py`)
   - Fetch current VIX value
   - Calculate 5-day and 20-day moving averages
   - Calculate daily percent change
   - Detect VIX spikes (change > 20%)
   - Return normalized score (-100 to 100)

2. **Market Breadth Indicator** (`src/market_mood/indicators/breadth.py`)
   - Calculate Advance/Decline ratio
   - Calculate Advance/Decline line
   - Calculate New Highs-Lows percentage
   - Detect divergence signals
   - Return normalized score

3. **Fear & Greed Indicator** (`src/market_mood/indicators/fear_greed.py`)
   - Implement internal calculation using 7 components
   - Or fetch from CNN website (scraping)
   - Handle fallback to VIX if unavailable
   - Return normalized score

4. **Put/Call Ratio Indicator** (`src/market_mood/indicators/put_call.py`)
   - Fetch CBOE Put/Call ratio
   - Calculate 5-day moving average
   - Detect ratio spikes
   - Return normalized score

5. **Moving Average Trend Indicator** (`src/market_mood/indicators/ma_trend.py`)
   - Fetch S&P 500 data
   - Calculate 20-day, 50-day, 200-day MAs
   - Detect golden/death crosses
   - Calculate position above/below MAs
   - Return normalized score

**Scoring Algorithm (per indicator):**
```python
def normalize_indicator(value, min_threshold, max_threshold, weight):
    """
    Normalize indicator value to -100 to 100 scale.
    Positive = bullish, Negative = bearish.
    """
    if value <= min_threshold:
        return -100 * weight
    elif value >= max_threshold:
        return 100 * weight
    else:
        # Linear interpolation
        normalized = (value - min_threshold) / (max_threshold - min_threshold)
        return (normalized * 2 - 1) * 100 * weight
```

**Deliverables:**
- 5 indicator implementations
- Indicator normalization logic
- Unit tests for each indicator
- Integration tests

**Acceptance Criteria:**
- All indicators return valid scores (-100 to 100)
- Error handling for missing data
- Unit tests with >80% coverage
- Integration with caching layer

---

### Phase 3: Mood Calculation Engine (Days 8-10)

**Objective:** Create composite mood score and signal generation

**Tasks:**

1. **Create Mood Engine** (`src/market_mood/engine.py`)
   ```python
   class MoodEngine:
       def __init__(self, config: dict):
           self.indicators = {
               'vix': VIXIndicator(weight=0.20),
               'breadth': BreadthIndicator(weight=0.15),
               'fear_greed': FearGreedIndicator(weight=0.20),
               'put_call': PutCallIndicator(weight=0.15),
               'ma_trend': MATrendIndicator(weight=0.10),
               'ad_line': ADLineIndicator(weight=0.10),
               'highs_lows': HighsLowsIndicator(weight=0.10),
           }
           self.thresholds = config['thresholds']
       
       def calculate_mood(self) -> MoodScore:
           # 1. Fetch all indicator data
           # 2. Normalize each indicator score
           # 3. Calculate weighted average
           # 4. Determine classification
           # 5. Calculate trend
           # 6. Calculate confidence
           pass
       
       def calculate_trend(self, historical_scores: List[float]) -> str:
           # Calculate trend: improving, declining, stable
           pass
       
       def calculate_confidence(self, scores: Dict[str, float]) -> float:
           # Calculate confidence based on consensus
           pass
   ```

2. **Implement Trend Detection**
   - Compare current score to 5-day, 10-day, 20-day averages
   - Use linear regression for trend slope
   - Classify as: "strongly_improving", "improving", "stable", "declining", "strongly_declining"

3. **Implement Confidence Scoring**
   - Measure agreement between indicators
   - Higher confidence when indicators agree
   - Lower confidence when conflicting

4. **Create Signal Generator** (`src/market_mood/signals.py`)
   ```python
   class SignalGenerator:
       def generate_trading_signals(self, mood: MoodScore) -> Dict:
           """Generate trading signals based on mood."""
           
           # Mood classification thresholds
           thresholds = {
               'extreme_fear': -70,
               'fear': -30,
               'neutral_low': -30,
               'neutral_high': 30,
               'greed': 70,
               'extreme_greed': 100
           }
           
           signals = {
               'action': 'HOLD',
               'strength': 'weak',
               'reasoning': '',
               'suggested_actions': []
           }
           
           if mood.overall_score <= thresholds['extreme_fear']:
               signals['action'] = 'BUY'
               signals['strength'] = 'strong'
               signals['reasoning'] = 'Market in extreme fear - contrarian buying opportunity'
               signals['suggested_actions'] = [
                   'Increase exposure by 10-20%',
                   'Focus on oversold quality stocks',
                   'Use dollar-cost averaging'
               ]
           elif mood.overall_score <= thresholds['fear']:
               signals['action'] = 'BUY'
               signals['strength'] = 'moderate'
               signals['reasoning'] = 'Market fearful - cautious buying'
               signals['suggested_actions'] = [
                   'Increase exposure by 5-10%',
                   'Look for value opportunities'
               ]
           # ... etc for each classification
           
           return signals
   ```

**Deliverables:**
- MoodEngine class
- Trend detection algorithm
- Confidence scoring
- Signal generator
- Unit tests

**Acceptance Criteria:**
- Composite score combines all indicators correctly
- Trend detection is accurate
- Confidence reflects indicator agreement
- Signals align with contrarian principles

---

### Phase 4: Integration (Days 11-13)

**Objective:** Integrate with existing system

**Tasks:**

1. **Create MarketMoodDetector Main Class** (`src/market_mood/detector.py`)
   ```python
   class MarketMoodDetector:
       def __init__(self, config: dict):
           self.engine = MoodEngine(config)
           self.cache = Cache()
       
       async def get_current_mood(self) -> MoodScore:
           """Get current market mood."""
           return await self.engine.calculate_mood()
       
       async def get_mood_history(self, days: int = 30) -> List[MoodScore]:
           """Get historical mood data."""
           pass
       
       async def get_trading_signals(self) -> Dict:
           """Get trading signals based on mood."""
           mood = await self.get_current_mood()
           generator = SignalGenerator()
           return generator.generate_trading_signals(mood)
   ```

2. **Create LangGraph Node** (`src/trading_graph/nodes/market_mood_node.py`)
   ```python
   async def market_mood_analysis(state: TradingState) -> Dict[str, Any]:
       """
       Analyze market mood and adjust trading signals accordingly.
       
       This node runs after technical and sentiment analysis.
       It provides market-wide context to the final decision.
       """
       detector = MarketMoodDetector()
       mood = await detector.get_current_mood()
       signals = await detector.get_trading_signals()
       
       return {
           "market_mood": mood.dict(),
           "market_signals": signals,
           "timestamp": get_utc_now()
       }
   ```

3. **Update LangGraph Graph** (`src/trading_graph/graph.py`)
   - Add `market_mood` node after `sentiment` node
   - Update conditional routing
   - Pass market mood to decision node

4. **Create API Routes** (`src/api/routes/market_mood.py`)
   ```python
   router = APIRouter(prefix="/api/market/mood", tags=["Market Mood"])

   @router.get("/")
   async def get_current_mood():
       """Get current market mood snapshot."""
       detector = MarketMoodDetector()
       mood = await detector.get_current_mood()
       return mood

   @router.get("/history")
   async def get_mood_history(days: int = 30):
       """Get historical mood data."""
       detector = MarketMoodDetector()
       history = await detector.get_mood_history(days)
       return {"history": history}

   @router.get("/indicators")
   async def get_individual_indicators():
       """Get individual indicator values."""
       # Return all indicator raw data
       pass

   @router.get("/signals")
   async def get_trading_signals():
       """Get trading signals based on mood."""
       detector = MarketMoodDetector()
       signals = await detector.get_trading_signals()
       return signals
   ```

5. **Update Configuration** (`src/config.py`)
   ```python
   # Market Mood Configuration
   market_mood_enabled: bool = True
   market_mood_cache_ttl: int = 900  # 15 minutes
   market_mood_update_interval: int = 3600  # 1 hour
   
   # Market Mood Thresholds
   mood_extreme_fear_threshold: float = -70
   mood_fear_threshold: float = -30
   mood_greed_threshold: float = 30
   mood_extreme_greed_threshold: float = 70
   ```

6. **Create Database Schema** (`src/market_mood/models.py` - SQLAlchemy)
   ```python
   class MoodHistory(Base):
       __tablename__ = "mood_history"
       
       id = Column(Integer, primary_key=True)
       timestamp = Column(DateTime, default=get_utc_now)
       overall_score = Column(Integer)
       classification = Column(String)
       confidence = Column(Float)
       trend = Column(String)
       vix_score = Column(Float)
       breadth_score = Column(Float)
       fear_greed_score = Column(Float)
       put_call_score = Column(Float)
       ma_trend_score = Column(Float)
   ```

**Deliverables:**
- MarketMoodDetector class
- LangGraph node integration
- API routes
- Database schema
- Updated configuration

**Acceptance Criteria:**
- MarketMoodDetector successfully retrieves mood data
- LangGraph node executes without errors
- API endpoints return valid data
- Mood history saved to database

---

### Phase 5: Testing & Optimization (Days 14-17)

**Objective:** Ensure system reliability and performance

**Tasks:**

1. **Unit Tests** (`tests/market_mood/`)
   - Test each indicator independently
   - Test mood engine calculations
   - Test signal generation
   - Test caching logic
   - Test error handling

2. **Integration Tests**
   - Test end-to-end flow
   - Test LangGraph node integration
   - Test API endpoints
   - Test database persistence

3. **Backtesting**
   - Backtest mood signals over 1-3 year period
   - Calculate performance metrics:
     - Win rate
     - Average return
     - Max drawdown
     - Sharpe ratio
   - Optimize thresholds based on results

4. **Performance Testing**
   - Measure API response times (< 500ms target)
   - Test with concurrent requests
   - Monitor cache hit rate (> 80% target)

5. **Load Testing**
   - Simulate 1000 requests/minute
   - Monitor memory usage
   - Test rate limiting

6. **Alert System**
   - Create alerts for extreme mood conditions
   - Email/webhook notifications
   - Dashboard alerts

**Deliverables:**
- Comprehensive test suite
- Backtest results report
- Performance metrics
- Alert system
- Optimization recommendations

**Acceptance Criteria:**
- > 90% test coverage
- API response time < 500ms
- Cache hit rate > 80%
- Backtest shows positive edge

---

## Mood Calculation Algorithm

### Composite Score Calculation

```python
class MoodEngine:
    def __init__(self):
        # Indicator weights (sum to 1.0)
        self.weights = {
            'vix': 0.20,
            'breadth': 0.15,
            'fear_greed': 0.20,
            'put_call': 0.15,
            'ma_trend': 0.10,
            'ad_line': 0.10,
            'highs_lows': 0.10,
        }
    
    def calculate_mood(self) -> MoodScore:
        """Calculate composite market mood score."""
        
        # 1. Fetch individual indicator scores
        scores = {}
        for name, indicator in self.indicators.items():
            data = indicator.fetch()
            scores[name] = indicator.normalize(data)
        
        # 2. Calculate weighted composite score
        composite_score = sum(
            scores[name] * self.weights[name]
            for name in self.weights.keys()
        )
        
        # 3. Clamp score to -100 to 100 range
        composite_score = max(-100, min(100, composite_score))
        
        # 4. Determine classification
        classification = self._classify(composite_score)
        
        # 5. Calculate confidence
        confidence = self._calculate_confidence(scores)
        
        # 6. Determine trend
        trend = self._calculate_trend(composite_score)
        
        return MoodScore(
            overall_score=int(composite_score),
            classification=classification,
            confidence=confidence,
            trend=trend,
            indicators=scores,
            timestamp=datetime.utcnow()
        )
    
    def _classify(self, score: float) -> str:
        """Classify mood score into descriptive category."""
        if score <= -70:
            return "extreme_fear"
        elif score <= -30:
            return "fear"
        elif score <= 30:
            return "neutral"
        elif score <= 70:
            return "greed"
        else:
            return "extreme_greed"
    
    def _calculate_confidence(self, scores: Dict[str, float]) -> float:
        """Calculate confidence based on indicator agreement."""
        values = list(scores.values())
        
        # Calculate standard deviation
        std_dev = statistics.stdev(values) if len(values) > 1 else 0
        
        # Lower std_dev = higher confidence (indicators agree)
        # Normalize: 0 std_dev = 1.0 confidence, high std_dev = 0.3 confidence
        confidence = max(0.3, 1.0 - (std_dev / 50.0))
        
        return round(confidence, 2)
    
    def _calculate_trend(self, current_score: float) -> str:
        """Calculate trend based on historical scores."""
        historical = self._get_historical_scores(days=5)
        
        if not historical:
            return "unknown"
        
        # Calculate linear regression slope
        x = list(range(len(historical)))
        y = historical
        slope = self._linear_regression_slope(x, y)
        
        # Classify trend
        if slope > 2:
            return "strongly_improving"
        elif slope > 0.5:
            return "improving"
        elif slope > -0.5:
            return "stable"
        elif slope > -2:
            return "declining"
        else:
            return "strongly_declining"
    
    def _linear_regression_slope(self, x: List[int], y: List[float]) -> float:
        """Calculate slope of linear regression."""
        n = len(x)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(xi * yi for xi, yi in zip(x, y))
        sum_x2 = sum(xi * xi for xi in x)
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
        return slope
```

### Trading Signal Generation

```python
class SignalGenerator:
    def generate_trading_signals(self, mood: MoodScore) -> Dict:
        """Generate trading signals based on mood."""
        
        signals = {
            'action': 'HOLD',
            'strength': 'weak',
            'position_adjustment': 0,  # -10 to +10 percentage points
            'reasoning': '',
            'suggested_actions': [],
            'warnings': []
        }
        
        score = mood.overall_score
        confidence = mood.confidence
        trend = mood.trend
        
        # Extreme Fear: Strong BUY signal
        if score <= -70:
            signals['action'] = 'BUY'
            signals['strength'] = 'strong' if confidence > 0.7 else 'moderate'
            signals['position_adjustment'] = 10 if confidence > 0.7 else 5
            signals['reasoning'] = (
                f"Market in extreme fear (score: {score}). "
                "Historically, this presents contrarian buying opportunities."
            )
            signals['suggested_actions'] = [
                'Increase portfolio exposure by 10-20%',
                'Focus on quality stocks with strong fundamentals',
                'Use dollar-cost averaging to reduce timing risk',
                'Consider defensive sectors for partial allocation'
            ]
            signals['warnings'] = [
                'Markets may fall further before reversing',
                'Maintain stop-loss discipline',
                'Avoid catching falling knives in fundamentally weak stocks'
            ]
        
        # Fear: BUY signal
        elif score <= -30:
            signals['action'] = 'BUY'
            signals['strength'] = 'moderate'
            signals['position_adjustment'] = 5
            signals['reasoning'] = (
                f"Market showing fear (score: {score}). "
                "Cautious buying opportunities emerging."
            )
            signals['suggested_actions'] = [
                'Increase exposure by 5-10%',
                'Look for value in oversold quality stocks',
                'Scale into positions gradually'
            ]
        
        # Neutral: HOLD signal
        elif score <= 30:
            signals['action'] = 'HOLD'
            signals['strength'] = 'weak'
            signals['position_adjustment'] = 0
            signals['reasoning'] = (
                f"Market sentiment neutral (score: {score}). "
                "Normal trading conditions."
            )
            signals['suggested_actions'] = [
                'Maintain current allocation',
                'Trade based on individual stock signals',
                'Use market mood as context, not primary driver'
            ]
        
        # Greed: SELL/Take Profits signal
        elif score <= 70:
            signals['action'] = 'SELL'
            signals['strength'] = 'moderate'
            signals['position_adjustment'] = -5
            signals['reasoning'] = (
                f"Market showing greed (score: {score}). "
                "Consider taking profits and reducing exposure."
            )
            signals['suggested_actions'] = [
                'Reduce exposure by 5-10%',
                'Take profits on extended winners',
                'Raise stop-loss levels on remaining positions',
                'Increase cash allocation'
            ]
        
        # Extreme Greed: Strong SELL signal
        else:  # score > 70
            signals['action'] = 'SELL'
            signals['strength'] = 'strong' if confidence > 0.7 else 'moderate'
            signals['position_adjustment'] = -10 if confidence > 0.7 else -5
            signals['reasoning'] = (
                f"Market in extreme greed (score: {score}). "
                "Historically, this precedes market corrections."
            )
            signals['suggested_actions'] = [
                'Reduce portfolio exposure by 10-20%',
                'Take profits aggressively',
                'Increase cash reserves significantly',
                'Consider defensive positions (bonds, utilities, staples)'
            ]
            signals['warnings'] = [
                'Market corrections can be rapid',
                'Avoid FOMO-driven buying',
                'Protect gains by tightening stops'
            ]
        
        # Adjust signals based on trend
        if trend == 'strongly_declining' and signals['action'] == 'BUY':
            signals['warnings'].append(
                'Strongly declining trend - be cautious with new buys'
            )
            signals['strength'] = 'weak'
        
        elif trend == 'strongly_improving' and signals['action'] == 'SELL':
            signals['warnings'].append(
                'Strongly improving trend - consider holding winners longer'
            )
            signals['strength'] = 'weak'
        
        return signals
```

---

## API Design

### Endpoint Specifications

#### 1. GET /api/market/mood - Current Mood Snapshot

**Description:** Get current market mood with all indicator details.

**Request:**
```
GET /api/market/mood
```

**Response:**
```json
{
  "overall_score": -45,
  "classification": "fear",
  "confidence": 0.78,
  "trend": "improving",
  "timestamp": "2026-02-11T14:30:00Z",
  "indicators": {
    "vix": {
      "score": -30,
      "value": 28.5,
      "change_pct": 15.2,
      "threshold_crossed": false
    },
    "breadth": {
      "score": -20,
      "ad_ratio": 0.65,
      "new_highs_lows_pct": 25
    },
    "fear_greed": {
      "score": -50,
      "value": 18,
      "classification": "fear"
    },
    "put_call": {
      "score": -35,
      "ratio": 1.15,
      "ma5": 1.05
    },
    "ma_trend": {
      "score": -10,
      "position": "below_200ma",
      "golden_cross": false,
      "death_cross": true
    }
  }
}
```

---

#### 2. GET /api/market/mood/history - Historical Mood Data

**Description:** Get historical mood scores for charting and analysis.

**Request:**
```
GET /api/market/mood/history?days=30
```

**Query Parameters:**
- `days` (optional): Number of days to retrieve (default: 30, max: 365)

**Response:**
```json
{
  "history": [
    {
      "date": "2026-02-11",
      "score": -45,
      "classification": "fear",
      "confidence": 0.78,
      "indicators": {
        "vix_score": -30,
        "breadth_score": -20,
        "fear_greed_score": -50,
        "put_call_score": -35,
        "ma_trend_score": -10
      }
    },
    {
      "date": "2026-02-10",
      "score": -40,
      "classification": "fear",
      "confidence": 0.72,
      "indicators": {...}
    }
  ]
}
```

---

#### 3. GET /api/market/mood/indicators - Individual Indicator Values

**Description:** Get raw values for each indicator.

**Request:**
```
GET /api/market/mood/indicators
```

**Response:**
```json
{
  "vix": {
    "current_value": 28.5,
    "change_pct": 15.2,
    "ma5": 24.2,
    "ma20": 22.8,
    "spike_detected": false
  },
  "breadth": {
    "advancing": 1850,
    "declining": 2845,
    "ad_ratio": 0.65,
    "ad_line": -4500,
    "new_highs": 85,
    "new_lows": 125,
    "highs_lows_pct": 40.5
  },
  "fear_greed": {
    "overall_score": 18,
    "classification": "fear",
    "components": {
      "momentum": 25,
      "price_strength": 15,
      "breadth": 20,
      "put_call": 22,
      "volatility": 10,
      "safe_haven": 30,
      "junk_bonds": 35
    }
  },
  "put_call": {
    "current_ratio": 1.15,
    "ma5": 1.05,
    "ma20": 0.95,
    "spike_detected": false
  },
  "ma_trend": {
    "sp500_price": 4150.25,
    "ma20": 4180.50,
    "ma50": 4220.75,
    "ma200": 4350.00,
    "golden_cross": false,
    "death_cross": true,
    "days_since_cross": 15
  }
}
```

---

#### 4. GET /api/market/mood/signals - Trading Signals

**Description:** Get trading signals based on current market mood.

**Request:**
```
GET /api/market/mood/signals
```

**Response:**
```json
{
  "action": "BUY",
  "strength": "moderate",
  "position_adjustment": 5,
  "reasoning": "Market showing fear (score: -45). Cautious buying opportunities emerging.",
  "suggested_actions": [
    "Increase exposure by 5-10%",
    "Look for value in oversold quality stocks",
    "Scale into positions gradually"
  ],
  "warnings": [
    "Markets may fall further before reversing",
    "Maintain stop-loss discipline"
  ],
  "mood_context": {
    "score": -45,
    "classification": "fear",
    "trend": "improving"
  },
  "generated_at": "2026-02-11T14:30:00Z"
}
```

---

#### 5. POST /api/market/mood/alerts - Subscribe to Mood Alerts

**Description:** Subscribe to alerts for extreme mood conditions.

**Request:**
```json
{
  "webhook_url": "https://example.com/webhook/mood-alerts",
  "thresholds": {
    "extreme_fear": true,
    "extreme_greed": true,
    "fear": false,
    "greed": false
  },
  "channels": ["webhook", "email"]
}
```

**Response:**
```json
{
  "subscription_id": "sub_12345",
  "status": "active",
  "created_at": "2026-02-11T14:30:00Z"
}
```

**Alert Payload (when threshold triggered):**
```json
{
  "alert_type": "extreme_fear",
  "current_score": -78,
  "threshold": -70,
  "timestamp": "2026-02-11T14:30:00Z",
  "message": "Market entered extreme fear zone (-78). Consider contrarian buying opportunities."
}
```

---

## Cost Analysis

### Data Source Cost Comparison

| Data Source | Type | Monthly Cost | API Limits | Notes |
|-------------|------|--------------|------------|-------|
| **Yahoo Finance** | Free | $0 | 5 requests/second | Recommended for VIX, S&P 500, Put/Call |
| **CBOE Website** | Free | $0 | None (scraping) | Put/Call ratio, historical data |
| **Alpha Vantage** | Free | $0 | 25 requests/day | Backup option |
| **Alpha Vantage** | Paid | $0.005/request | Unlimited | For premium features |
| **Investopedia/FactSet** | Paid | $50-100/month | Unlimited | Real-time breadth data |
| **Bloomberg API** | Paid | $1000+/month | Unlimited | Not recommended |

### Recommended Implementation: Free Sources

**Total Monthly Cost: $0**

**Breakdown:**
1. **Yahoo Finance** - $0
   - VIX data (^VIX)
   - S&P 500 data (^GSPC)
   - Put/Call ratio (^CBOE)
   - Historical data (up to 60 days)

2. **CBOE Website** - $0
   - Daily Put/Call ratio CSV
   - Historical Put/Call ratio
   - VIX historical data (as backup)

3. **Internal Calculation** - $0
   - Fear & Greed: Calculate internally using components
   - Market Breadth: Calculate from stock data

### API Call Estimates

**Daily API Calls:**
- VIX fetch: 1 call (cached for 15 min = 4 calls/day)
- S&P 500 fetch: 1 call (cached for 1 hour = 24 calls/day)
- Put/Call ratio: 1 call (cached for 15 min = 4 calls/day)
- Market breadth: 10 calls (cached for 15 min = 40 calls/day)
- Fear & Greed: 7 component calls (cached for 1 hour = 168 calls/day)

**Total: ~240 calls/day**

**With 15-minute cache: ~40 actual API calls/day (83% reduction)**

### Cost-Effective Implementation Strategy

1. **Primary Strategy: Free Sources + Aggressive Caching**
   - Use Yahoo Finance as primary source
   - Cache all data for 15-60 minutes
   - Implement fallback to cached data on API failures
   - Total cost: $0/month

2. **Fallback Strategy: Alpha Vantage Free Tier**
   - 25 free requests/day for backup data
   - Use only when Yahoo Finance fails
   - Total cost: $0/month

3. **Premium Strategy: Paid Breadth Data**
   - If real-time breadth is critical
   - Subscribe to real-time breadth service
   - Estimated cost: $50-100/month
   - **Recommendation: Start with free, upgrade if needed**

### ROI Analysis

**Expected Benefits:**
- Improved market timing: +2-5% annual return
- Better risk management: Reduced drawdowns by 10-20%
- Enhanced signal quality: Higher win rates on trades

**Break-even:** With $100K portfolio, 2% improvement = $2,000/year ROI

**Conclusion:** Free implementation provides excellent ROI. Premium data sources only needed for high-frequency trading.

---

## Testing Strategy

### Unit Tests

**Coverage Target: > 90%**

**Test Files:**
```
tests/market_mood/
├── test_detector.py
├── test_engine.py
├── test_signals.py
├── test_indicators/
│   ├── test_vix.py
│   ├── test_breadth.py
│   ├── test_fear_greed.py
│   ├── test_put_call.py
│   └── test_ma_trend.py
└── test_data_providers/
    ├── test_yahoo_provider.py
    └── test_cboe_provider.py
```

**Test Cases:**
- Indicator normalization logic
- Composite score calculation
- Trend detection
- Confidence scoring
- Signal generation
- Error handling
- Cache invalidation
- Rate limiting

### Integration Tests

**Test Scenarios:**
1. End-to-end mood calculation
2. LangGraph node integration
3. API endpoint functionality
4. Database persistence
5. Cache consistency

### Backtesting

**Methodology:**
1. Collect historical data for 3 years
2. Calculate daily mood scores retrospectively
3. Simulate trading based on mood signals
4. Compare against buy-and-hold baseline

**Metrics:**
- Total return
- Win rate
- Max drawdown
- Sharpe ratio
- Calmar ratio

### Performance Tests

**Targets:**
- API response time: < 500ms (95th percentile)
- Cache hit rate: > 80%
- Concurrent requests: 1000/minute

---

## Timeline

### Week 1: Data Infrastructure & Core Indicators
- **Day 1:** Setup project structure, base provider class
- **Day 2:** Implement Yahoo Finance provider, caching layer
- **Day 3:** Implement CBOE provider, data models
- **Day 4:** Implement VIX indicator
- **Day 5:** Implement Market Breadth indicator

### Week 2: Complete Indicators & Engine
- **Day 6:** Implement Fear & Greed indicator
- **Day 7:** Implement Put/Call ratio indicator
- **Day 8:** Implement MA Trend indicator
- **Day 9:** Build Mood Engine
- **Day 10:** Build Signal Generator

### Week 3: Integration & Testing
- **Day 11:** Create MarketMoodDetector class
- **Day 12:** Integrate with LangGraph
- **Day 13:** Create API routes
- **Day 14:** Unit tests
- **Day 15:** Integration tests
- **Day 16:** Backtesting
- **Day 17:** Performance optimization

### Week 4: Documentation & Deployment
- **Day 18:** Documentation (API docs, user guide)
- **Day 19:** Dashboard integration
- **Day 20:** Staging deployment
- **Day 21:** Production deployment
- **Day 22:** Monitoring setup
- **Day 23:** Final review
- **Day 24:** Handoff

**Total Timeline: 4-5 weeks**

---

## Risk Mitigation

### Technical Risks

| Risk | Probability | Impact | Mitigation Strategy |
|------|-------------|--------|-------------------|
| API rate limits | Medium | High | Aggressive caching, fallback providers |
| Data source changes | Low | Medium | Abstracted provider layer, multiple sources |
| Incorrect indicator calculations | Low | High | Extensive unit tests, validation against known values |
| Cache invalidation issues | Low | Medium | TTL-based expiration, manual invalidation |
| Performance degradation | Low | Medium | Load testing, query optimization |

### Market Risks

| Risk | Probability | Impact | Mitigation Strategy |
|------|-------------|--------|-------------------|
| Indicators give false signals | High | Medium | Use composite score, multiple indicators |
| Contrarian strategy fails | Medium | High | Start with small position sizes, use as secondary signal |
| Market regime changes | Medium | Medium | Adaptive thresholds, continuous backtesting |

### Project Risks

| Risk | Probability | Impact | Mitigation Strategy |
|------|-------------|--------|-------------------|
| Delayed timeline | Medium | Low | Phased rollout, MVP first |
| Budget overruns | Low | Medium | Use free data sources, minimal external dependencies |
| Team resource constraints | Medium | Medium | Clear priorities, outsource non-critical tasks |

---

## Appendices

### Appendix A: Configuration File Example

```yaml
# config/market_mood_config.yaml
market_mood:
  enabled: true
  cache_ttl_seconds: 900  # 15 minutes
  update_interval_seconds: 3600  # 1 hour
  
indicators:
  vix:
    enabled: true
    weight: 0.20
    thresholds:
      low: 20
      high: 30
      extreme: 40
  
  breadth:
    enabled: true
    weight: 0.15
    thresholds:
      bullish: 1.5
      bearish: 0.5
  
  fear_greed:
    enabled: true
    weight: 0.20
    calculate_internally: true
  
  put_call:
    enabled: true
    weight: 0.15
    thresholds:
      greedy: 0.7
      fearful: 1.0
  
  ma_trend:
    enabled: true
    weight: 0.10
    periods: [20, 50, 200]

signals:
  extreme_fear_threshold: -70
  fear_threshold: -30
  neutral_low_threshold: -30
  neutral_high_threshold: 30
  greed_threshold: 70
  
alerts:
  enabled: true
  webhook_url: null
  email_recipients: []
  slack_webhook: null

data_providers:
  primary: "yahoo"
  fallback: "alpha_vantage"
  cache_enabled: true
```

### Appendix B: Environment Variables

```bash
# Market Mood Configuration
MARKET_MOOD_ENABLED=true
MARKET_MOOD_CACHE_TTL=900

# Data Provider Settings
YAHOO_FINANCE_RATE_LIMIT=5  # requests/second
CBOE_SCRAPING_ENABLED=true

# Alert Settings
MARKET_MOOD_ALERTS_ENABLED=true
MARKET_MOOD_WEBHOOK_URL=
MARKET_MOOD_EMAIL_RECIPIENTS=

# API Keys (for paid services if needed)
ALPHA_VANTAGE_API_KEY=
FACTSET_API_KEY=
```

### Appendix C: Dependencies to Add

```txt
# New dependencies for Market Mood Detection
yfinance>=0.2.32              # Yahoo Finance data (may already exist)
beautifulsoup4>=4.12.0        # Web scraping
requests>=2.31.0              # HTTP requests (may already exist)
lxml>=4.9.0                   # XML/HTML parsing
pandas>=2.0.0                 # Data analysis (may already exist)
numpy>=1.24.0                 # Numerical computing (may already exist)
scipy>=1.10.0                # Statistical functions
```

---

## Conclusion

This implementation plan provides a comprehensive roadmap for developing the Market Mood Detection feature for TradeMind AI. The feature will:

1. **Leverage free data sources** to minimize costs
2. **Integrate seamlessly** with the existing LangGraph workflow
3. **Provide valuable contrarian signals** for enhanced trading performance
4. **Use aggressive caching** to minimize API calls and improve performance

**Next Steps:**
1. Review and approve this implementation plan
2. Set up project structure
3. Begin Phase 1: Data Infrastructure

**Questions for Review:**
1. Should we prioritize any specific indicator?
2. Are there additional indicators to consider?
3. What is the target deployment date?
4. Any budget constraints for paid data sources?

---

**Document Version History:**
- v1.0 (Feb 11, 2026): Initial implementation plan
