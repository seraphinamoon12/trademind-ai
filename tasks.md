# TradeMind AI - Development Tasks

## Sentiment Agent Improvements (From Code Review)

### 🔴 Critical Priority

#### 1. Fix Config Naming Inconsistency ✅
- **Issue:** `zai_api_key` vs `zai_api_token` naming mismatch between config and agent
- **Impact:** May break in production
- **Files:** `src/config.py`, `src/agents/sentiment.py`
- **Action:** Align naming convention across codebase

#### 2. Refactor to Async HTTP Client ✅
- **Issue:** Using sync `httpx.post` instead of async `httpx.AsyncClient`
- **Impact:** Performance bottleneck, blocks event loop
- **File:** `src/agents/sentiment.py`
- **Action:** Replace with `async with httpx.AsyncClient() as client:`

#### 3. Move Imports to Top of File ✅
- **Issue:** `import re` inside method `_parse_sentiment_text`
- **Impact:** Code smell, repeated import overhead
- **File:** `src/agents/sentiment.py`
- **Action:** Move all imports to top of file

---

### 🟡 Medium Priority

#### 4. Add Retry Logic with Exponential Backoff ✅
- **Issue:** No retry mechanism for API failures
- **Impact:** Temporary API issues cause complete failure
- **File:** `src/agents/sentiment.py`
- **Action:** Add `@retry` decorator or manual retry loop
- **Example:**
  ```python
  @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
  async def _analyze_with_zai(self, ...)
  ```

#### 5. Move Hardcoded Values to Config ✅
- **Issue:** Hardcoded `temperature=0.3`, model name, timeouts
- **Impact:** Difficult to tune without code changes
- **Files:** `src/agents/sentiment.py`, `src/config.py`
- **Action:** Add to Settings class:
  - `zai_model: str = "glm-4.7"`
  - `zai_temperature: float = 0.3`
  - `zai_timeout: int = 30`

#### 6. Add Confidence Validation
- **Issue:** No validation that confidence is within 0-1 range
- **Impact:** Invalid values could propagate
- **File:** `src/agents/sentiment.py`
- **Action:** Add validation in `_sentiment_to_signal` method

#### 7. Improve Fallback Confidence Calculation
- **Issue:** Fallback uses hardcoded confidence (0.5, 0.8)
- **Impact:** Not proportional to actual momentum
- **File:** `src/agents/sentiment.py`
- **Action:** Calculate confidence from price momentum magnitude

#### 8. Add Sentiment Caching
- **Issue:** Re-analyzing same symbol multiple times
- **Impact:** Unnecessary API calls and latency
- **File:** `src/agents/sentiment.py`
- **Action:** Cache results for 15-30 minutes per symbol
- **Implementation:** Use Redis or in-memory cache with TTL

#### 9. Enhance Fallback Logic
- **Issue:** Simple momentum-based fallback
- **Impact:** Misses volume and other signals
- **File:** `src/agents/sentiment.py`
- **Action:** Add volume trend, RSI, MACD to fallback analysis

---

### 🟢 Low Priority / Nice to Have

#### 10. Add Debug Logging for API Calls
- **File:** `src/agents/sentiment.py`
- **Action:** Log API requests/responses at DEBUG level
- **Benefit:** Easier troubleshooting

#### 11. Add Unit/Integration Tests
- **Files:** `tests/test_sentiment_agent.py`
- **Coverage:**
  - API success/failure scenarios
  - JSON parsing
  - Text parsing fallback
  - Fallback logic
  - Config loading

#### 12. Add Circuit Breaker Pattern
- **File:** `src/agents/sentiment.py`
- **Action:** Stop calling API after N consecutive failures
- **Benefit:** Prevent cascading failures

#### 13. Multi-Timeframe Analysis
- **File:** `src/agents/sentiment.py`
- **Action:** Analyze 1d, 1w, 1m timeframes
- **Benefit:** More robust sentiment signal

#### 14. Store Sentiment History
- **Files:** `src/agents/sentiment.py`, `src/core/database.py`
- **Action:** Save sentiment results to database
- **Benefit:** Track sentiment trends over time

#### 15. Weight Confidence by Volatility
- **File:** `src/agents/sentiment.py`
- **Action:** Reduce confidence in high-volatility periods
- **Benefit:** More reliable signals

---

## Prompt Engineering Improvements

#### 16. Add Few-Shot Examples
- **File:** `src/agents/sentiment.py`
- **Action:** Include 2-3 examples in the prompt
- **Benefit:** Better formatted, consistent responses

#### 17. Include Market Context
- **File:** `src/agents/sentiment.py`
- **Action:** Add recent market events/news context
- **Benefit:** More informed sentiment analysis

#### 18. Ask for Key Factors
- **File:** `src/agents/sentiment.py`
- **Action:** Request key factors driving sentiment
- **Benefit:** Better explainability

#### 19. Chain-of-Thought Reasoning
- **File:** `src/agents/sentiment.py`
- **Action:** Ask LLM to reason step-by-step
- **Benefit:** More accurate sentiment classification

---

## Implementation Priority Order

1. Fix critical issues (1-3) - **Before production**
2. Add retry logic (4) - **Before production**
3. Move hardcoded values to config (5)
4. Add caching (8)
5. Improve fallback logic (9)
6. Add tests (11)
7. Add circuit breaker (12)
8. Implement prompt improvements (16-19)
9. Multi-timeframe and history (13-14)

---

## Notes

- Overall code structure is solid
- These improvements will improve reliability and maintainability
- Consider A/B testing sentiment signals before full deployment
- Monitor API costs with ZAI GLM-4.7

*Created: 2026-02-07*  
*Based on: OpenCode code review of sentiment agent implementation*

---

## Phase 1: Foundation Tasks

- [ ] Project structure with proper separation
- [ ] TimescaleDB setup for time-series data
- [ ] yfinance integration with caching
- [ ] Technical indicator library (pandas-ta)
- [ ] Event bus with Redis Pub/Sub
- [ ] Basic portfolio tracker (in-memory → DB)
- [ ] Rule-based strategy: RSI Mean Reversion
- [ ] Rule-based strategy: Moving Average Crossover

**Deliverable**: Can fetch data, calculate indicators, run backtests

---

## Phase 2: Strategy Engine Tasks

- [ ] Backtrader integration for backtesting
- [ ] 3+ rule-based strategies with parameters
- [ ] Realistic backtesting (slippage, latency simulation)
- [ ] Walk-forward analysis
- [ ] Paper trading execution engine
- [ ] Trade logging with reasoning
- [ ] Performance metrics (Sharpe, max drawdown, win rate)

**Deliverable**: Backtest shows realistic results, paper trading active

---

## Phase 3: AI Integration Tasks

- [ ] Sentiment agent with news analysis
- [ ] Strategy selection agent (chooses which rule-based strategy to use)
- [ ] Meta-strategy: Combine multiple rule-based signals
- [ ] Agent reasoning logging and explainability
- [ ] A/B testing: Compare rule-based vs AI-hybrid

**Deliverable**: AI enhances but doesn't replace rule-based strategies

---

## Phase 4: Dashboard & Polish Tasks

- [ ] FastAPI + HTMX dashboard
- [ ] Real-time portfolio updates (WebSocket or SSE)
- [ ] Performance charts with Plotly
- [ ] Strategy configuration UI
- [ ] Agent activity monitor
- [ ] Docker + deployment

**Deliverable**: Full web application, deployed and running

---

## Next Steps (Starting Phase 1)

1. ✅ Project folder created: `~/projects/trading-agent/`
2. 🔄 Set up Python environment (venv + dependencies)
3. 🔄 Initialize database (TimescaleDB via Docker)
4. 🔄 Create project structure
5. 🔄 Build market data ingestion pipeline
6. 🔄 Implement first strategy (RSI Mean Reversion)

---

## Safety Infrastructure Improvements

### Potential Enhancements (Future Work)

#### 1. Advanced Risk Metrics
- **Value at Risk (VaR)** calculation
- **Conditional VaR (CVaR)** implementation
- **Beta-adjusted position sizing**
- **Correlation matrix analysis** for portfolio risk

#### 2. Dynamic Safety Parameters
- **Adaptive circuit breaker thresholds** based on market volatility
- **Dynamic position limits** adjusted by market conditions
- **Time-based risk scaling** (reduce exposure during volatile periods)
- **Machine learning-based risk prediction**

#### 3. Enhanced Monitoring
- **Real-time anomaly detection** in trading patterns
- **Strategy drift monitoring** (detect when strategy degrades)
- **Live dashboard alerts** with push notifications
- **Automated reporting generation** (daily/weekly risk reports)

#### 4. Backtesting Safety Rules
- **Historical stress testing** of safety parameters
- **Monte Carlo simulations** for worst-case scenarios
- **Strategy safety validation** before deployment
- **Circuit breaker performance analysis** on historical data

#### 5. Additional Safety Layers
- **Pre-trade credit checks** for real money accounts
- **Order validation** (duplicate detection, size limits)
- **Position-level stop-loss automation**
- **Automated position reduction** on adverse market events

#### 6. Regulatory Compliance
- **Trade reporting** for audit trails
- **Position reporting** requirements
- **Pattern day trading** rules integration
- **SEC/FINRA compliance** checks

#### 7. Testing & Validation
- **Comprehensive safety test suite**
- **Integration tests** for all safety components
- **Performance benchmarking** of safety checks
- **Chaos engineering** for failure scenarios

---

## Database Schema Tasks

- [ ] Implement TimescaleDB hypertable for market_data
- [ ] Create indicators table with technical analysis values
- [ ] Create trades table with agent_signals JSONB field
- [ ] Create portfolio_snapshots table for historical tracking
- [ ] Create holdings table for current positions
- [ ] Create agent_decisions table for audit trail
- [ ] Add indexes for performance optimization
- [ ] Set up automatic data partitioning

---

## Micro-Agent Implementation Tasks

### Technical Analysis Agent
- [ ] Implement base agent class
- [ ] Add RSI calculation logic
- [ ] Add MACD calculation logic
- [ ] Add Moving Average calculations
- [ ] Add Bollinger Bands calculation
- [ ] Implement signal generation with confidence scores

### Sentiment Agent
- [ ] Implement news fetching from multiple sources
- [ ] Add LLM-based sentiment analysis
- [ ] Implement sentiment caching (15-30 min TTL)
- [ ] Add fallback to momentum-based sentiment
- [ ] Implement confidence scoring
- [ ] Add multi-timeframe sentiment analysis

### Risk Agent
- [ ] Implement position size validation
- [ ] Add sector concentration checks
- [ ] Implement stop-loss/take-profit logic
- [ ] Add correlation-based position limits
- [ ] Implement Kelly Criterion sizing
- [ ] Add daily loss limit enforcement

### Portfolio Agent
- [ ] Implement portfolio state management
- [ ] Add rebalancing logic
- [ ] Implement allocation tracking
- [ ] Add performance metrics calculation
- [ ] Implement position heat tracking
- [ ] Add automated rebalancing triggers

### Orchestrator
- [ ] Implement weighted voting mechanism
- [ ] Add signal combination logic
- [ ] Implement veto override for risk agent
- [ ] Add decision logging with reasoning
- [ ] Implement confidence aggregation
- [ ] Add A/B testing framework

---

## Configuration Management Tasks

- [ ] Create config.yaml with all parameters
- [ ] Implement environment-specific configs (dev/staging/prod)
- [ ] Add configuration validation
- [ ] Implement secure secrets management
- [ ] Add hot-reload for config changes
- [ ] Document all configuration parameters

---

## Testing Strategy Tasks

- [ ] Unit tests for all agents
- [ ] Integration tests for event bus
- [ ] Database migration tests
- [ ] Backtesting accuracy tests
- [ ] Safety rule validation tests
- [ ] Load testing for API endpoints
- [ ] End-to-end trading simulation tests
