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

---

## CLI Implementation Tasks

### File Structure Setup
- [ ] Create cli/ directory structure with __init__.py
- [ ] Create cli/main.py - Entry point with main CLI group
- [ ] Create cli/server.py - Server management commands (start, stop, status, logs, restart)
- [ ] Create cli/portfolio.py - Portfolio commands (portfolio, holdings, performance, sectors, export)
- [ ] Create cli/trades.py - Trade commands (list, show, export, today, pnl)
- [ ] Create cli/strategies.py - Strategy commands (list, enable, disable, config, set, performance, backtest)
- [ ] Create cli/safety.py - Safety commands (status, circuit-breaker, heat, emergency-stop, reset-circuit-breaker, limits, set)
- [ ] Create cli/backtest.py - Backtest commands (run, compare, results, list, export)
- [ ] Create cli/data.py - Data commands (ingest, status, show, update-indicators, clear-cache, verify)
- [ ] Create cli/config.py - Config commands (show, get, set, reset, validate, export, import)
- [ ] Create setup.py with CLI entry point configuration
- [ ] Create trademind executable script

### Dependencies Setup
- [ ] Add click>=8.0.0 to dependencies
- [ ] Add requests>=2.28.0 to dependencies
- [ ] Add tabulate>=0.9.0 to dependencies (table formatting)
- [ ] Add rich>=13.0.0 to dependencies (colored output)
- [ ] Add pyyaml>=6.0 to dependencies (config files)

### Server Management Implementation
- [ ] Implement server start command with --port and --reload options
- [ ] Implement server stop command (read PID from file, kill process)
- [ ] Implement server status command (check /health endpoint)
- [ ] Implement server logs command with --follow and --lines options
- [ ] Implement server restart command

### Portfolio Commands Implementation
- [ ] Implement portfolio summary command
- [ ] Implement portfolio holdings detailed view
- [ ] Implement portfolio performance command with --days option
- [ ] Implement portfolio sectors view
- [ ] Implement portfolio export with --format (csv|json) and --output options

### Trade Commands Implementation
- [ ] Implement trades list with --limit and --symbol options
- [ ] Implement trades show [trade_id] command
- [ ] Implement trades export with --start and --end date options
- [ ] Implement trades today command
- [ ] Implement trades pnl with --symbol option

### Strategy Commands Implementation
- [ ] Implement strategies list command
- [ ] Implement strategies enable [strategy] command
- [ ] Implement strategies disable [strategy] command
- [ ] Implement strategies config [strategy] command
- [ ] Implement strategies set [strategy] with parameter options (--oversold, --overbought)
- [ ] Implement strategies performance with --strategy option
- [ ] Implement strategies backtest [strategy] with --symbol and --days options

### Safety Commands Implementation
- [ ] Implement safety status command
- [ ] Implement safety circuit-breaker command
- [ ] Implement safety heat command
- [ ] Implement safety emergency-stop with --reason option
- [ ] Implement safety reset-circuit-breaker command
- [ ] Implement safety limits command
- [ ] Implement safety set command with --max-positions and other risk parameters

### Backtest Commands Implementation
- [ ] Implement backtest run with --strategy, --symbol, --symbols, and --days options
- [ ] Implement backtest compare with --strategies and --symbol options
- [ ] Implement backtest results [backtest_id] command
- [ ] Implement backtest list with --limit option
- [ ] Implement backtest export [backtest_id] with --format option

### Data Commands Implementation
- [ ] Implement data ingest with --symbols option
- [ ] Implement data status command
- [ ] Implement data show [symbol] with --days option
- [ ] Implement data update-indicators command
- [ ] Implement data clear-cache command
- [ ] Implement data verify command

### Config Commands Implementation
- [ ] Implement config show command
- [ ] Implement config get [key] command
- [ ] Implement config set [key] [value] command
- [ ] Implement config reset command
- [ ] Implement config validate command
- [ ] Implement config export command (output to stdout)
- [ ] Implement config import [file] command

### Interactive Mode
- [ ] Implement interactive shell (trademind shell)
- [ ] Add support for running commands within shell
- [ ] Implement exit command for shell

### Automation Features
- [ ] Add --format json option to relevant commands for scripting
- [ ] Document cron job examples for daily reports
- [ ] Document strategy rotation script examples
- [ ] Document health check script examples

### Testing
- [ ] Create tests/cli/test_server.py
- [ ] Create tests/cli/test_portfolio.py
- [ ] Create tests/cli/test_trades.py
- [ ] Create tests/cli/test_strategies.py
- [ ] Create tests/cli/test_safety.py
- [ ] Create tests/cli/test_backtest.py
- [ ] Create tests/cli/test_data.py
- [ ] Create tests/cli/test_config.py
- [ ] Add unit tests for all CLI commands
- [ ] Add integration tests for CLI-API interaction

### Documentation
- [ ] Implement --help for main CLI group
- [ ] Implement --help for all command groups
- [ ] Implement --help for all individual commands
- [ ] Create examples command with usage examples
- [ ] Document all CLI commands with examples

### Output Formatting
- [ ] Implement table formatting with tabulate for all list commands
- [ ] Add emoji indicators for status (✅, 🔴, 🟢)
- [ ] Use rich for colored output
- [ ] Add progress bars for long-running operations
- [ ] Format currency values consistently

### Error Handling
- [ ] Add graceful error handling for API failures
- [ ] Add validation for command options
- [ ] Provide helpful error messages
- [ ] Add retry logic for network calls
- [ ] Handle missing server connection gracefully

### Future Enhancements (Optional)
- [ ] WebSocket Mode - Real-time updates in terminal
- [ ] Dashboard Mode - `trademind dashboard` launches TUI
- [ ] Plugin System - Custom commands via plugins
- [ ] Remote Control - CLI for remote servers via SSH
- [ ] Notification Integration - Slack/Discord alerts via CLI

---

## Interactive Brokers Integration Tasks

### Week 1: Foundation

#### TWS Setup & Configuration
- [ ] Download and install TWS (Trader Workstation)
- [ ] Download and install IB Gateway (for production headless operation)
- [ ] Create IBKR paper trading account at interactivebrokers.com
- [ ] Log in to TWS/IB Gateway with paper account credentials
- [ ] Configure TWS API settings:
  - [ ] Navigate to Edit > Global Configuration > API > Settings
  - [ ] Enable "ActiveX and Socket Clients": YES
  - [ ] Set socket port: 7497 (paper) / 7496 (live)
  - [ ] Disable "Allow connections from localhost only" (for Docker)
  - [ ] Add trusted IP: 127.0.0.1
  - [ ] Uncheck "Read-Only API" (to allow trading)
- [ ] Verify API connection by connecting to port 7497
- [ ] Document TWS/IB Gateway authentication credentials securely

#### Dependencies Installation
- [ ] Add `ib_insync>=0.2.9` to requirements.txt
- [ ] Add `pandas>=2.0.0` to requirements.txt (if not already present)
- [ ] Run `pip install -r requirements.txt` to install dependencies
- [ ] Test ib_insync installation by importing the library
- [ ] Verify ib_insync version compatibility
- [ ] Install xvfb (X Virtual Framebuffer) for headless IB Gateway
- [ ] Install required system dependencies: libxtst6, libxi6, libxrender1

#### Project Structure Creation
- [ ] Create `src/brokers/` directory
- [ ] Create `src/brokers/__init__.py`
- [ ] Create `src/brokers/base.py` - Abstract broker interface
- [ ] Create `src/brokers/ibkr/` subdirectory
- [ ] Create `src/brokers/ibkr/__init__.py`
- [ ] Create `src/brokers/ibkr/client.py` - IBKRBroker class
- [ ] Create `src/brokers/ibkr/orders.py` - Order construction helpers
- [ ] Create `src/brokers/ibkr/positions.py` - Position tracking
- [ ] Create `src/brokers/ibkr/account.py` - Account info
- [ ] Create `src/brokers/ibkr/market_data.py` - Market data streaming
- [ ] Create `src/brokers/ibkr/utils.py` - Utility functions
- [ ] Create `src/brokers/ibkr/risk_checks.py` - Risk management
- [ ] Verify existing `src/brokers/paper/` directory structure
- [ ] Create `src/execution/` directory
- [ ] Create `src/execution/__init__.py`
- [ ] Create `src/execution/router.py` - Order routing
- [ ] Create `src/execution/factory.py` - Broker factory
- [ ] Create `config/ibkr_config.yaml` - IBKR configuration file

#### Abstract Broker Interface Implementation
- [ ] Define `Order` dataclass in `src/brokers/base.py`:
  - [ ] symbol: str
  - [ ] quantity: int
  - [ ] side: str ('BUY' or 'SELL')
  - [ ] order_type: str ('MARKET', 'LIMIT', 'STOP')
  - [ ] limit_price: Optional[Decimal]
  - [ ] stop_price: Optional[Decimal]
  - [ ] time_in_force: str ('DAY', 'GTC', 'IOC', 'FOK')
- [ ] Define `Position` dataclass in `src/brokers/base.py`:
  - [ ] symbol: str
  - [ ] quantity: int
  - [ ] avg_cost: Decimal
  - [ ] market_price: Decimal
  - [ ] market_value: Decimal
  - [ ] unrealized_pnl: Decimal
- [ ] Define `Account` dataclass in `src/brokers/base.py`:
  - [ ] account_id: str
  - [ ] cash_balance: Decimal
  - [ ] portfolio_value: Decimal
  - [ ] buying_power: Decimal
  - [ ] day_trades_remaining: int
- [ ] Define `BaseBroker` abstract class in `src/brokers/base.py`:
  - [ ] `async def connect(self) -> bool`
  - [ ] `async def disconnect(self)`
  - [ ] `async def place_order(self, order: Order) -> Dict`
  - [ ] `async def cancel_order(self, order_id: str) -> bool`
  - [ ] `async def get_positions(self) -> List[Position]`
  - [ ] `async def get_account(self) -> Account`
  - [ ] `async def get_orders(self, status: str = 'open') -> List[Dict]`
- [ ] Add docstrings to all abstract methods
- [ ] Add type hints to all method signatures

#### IBKR Connection Manager
- [ ] Implement `IBKRBroker` class in `src/brokers/ibkr/client.py`
- [ ] Import ib_insync components: IB, Stock, MarketOrder, LimitOrder, StopOrder
- [ ] Implement `__init__` method with parameters:
  - [ ] host: str = '127.0.0.1'
  - [ ] port: int = 7497
  - [ ] client_id: int = 1
- [ ] Initialize ib_insync IB instance
- [ ] Initialize connection state variables (_connected, _reconnecting)
- [ ] Implement `async def connect(self) -> bool`:
  - [ ] Call `await self.ib.connectAsync()`
  - [ ] Handle connection errors with try/except
  - [ ] Set _connected flag on success
  - [ ] Log connection status
  - [ ] Return success/failure boolean
- [ ] Implement `async def disconnect(self)`:
  - [ ] Check if connected before disconnecting
  - [ ] Call `self.ib.disconnect()`
  - [ ] Set _connected flag to False
- [ ] Add connection status property `is_connected`
- [ ] Test connection with TWS/IB Gateway running
- [ ] Test connection with TWS/IB Gateway stopped
- [ ] Test connection with incorrect port
- [ ] Test connection with invalid credentials
- [ ] Add logging for all connection events
- [ ] Add reconnection logic with retry attempts

#### Configuration Setup
- [ ] Create `config/ibkr_config.yaml` with following sections:
  - [ ] broker.type (ibkr or paper)
  - [ ] ibkr.host (127.0.0.1)
  - [ ] ibkr.port (7497 for paper, 7496 for live)
  - [ ] ibkr.client_id
  - [ ] ibkr.reconnect_attempts
  - [ ] ibkr.reconnect_delay (seconds)
  - [ ] ibkr.default_order_type
  - [ ] ibkr.time_in_force
  - [ ] ibkr.max_order_size (shares)
  - [ ] ibkr.max_order_value (dollars)
  - [ ] ibkr.market_data_type (delayed/realtime)
- [ ] Load IBKR config in `src/config.py`
- [ ] Add IBKR settings to Settings class
- [ ] Implement config validation for IBKR parameters
- [ ] Add environment variable support for sensitive settings
- [ ] Document all IBKR configuration parameters

---

### Week 2: Order Management

#### Order Type Mapping Implementation
- [ ] Create order type mapping table in `src/brokers/ibkr/orders.py`:
  - [ ] MARKET → MarketOrder
  - [ ] LIMIT → LimitOrder
  - [ ] STOP → StopOrder
  - [ ] STOP_LIMIT → StopLimitOrder
- [ ] Implement `create_ibkr_order()` function:
  - [ ] Accept TradeMind Order object as input
  - [ ] Create appropriate IBKR contract (Stock)
  - [ ] Map order type to IBKR order class
  - [ ] Set order parameters (action, quantity, prices)
  - [ ] Return (order, contract) tuple
- [ ] Implement contract qualification:
  - [ ] Add `await self.ib.qualifyContractsAsync()` call
  - [ ] Handle contract qualification failures
  - [ ] Log qualified contract details
- [ ] Add order validation:
  - [ ] Validate order quantity > 0
  - [ ] Validate order side is BUY or SELL
  - [ ] Validate order type is supported
  - [ ] Validate limit_price for LIMIT orders
  - [ ] Validate stop_price for STOP orders
- [ ] Test order mapping for all order types
- [ ] Test with invalid orders

#### Place Order Implementation
- [ ] Implement `async def place_order()` in `src/brokers/ibkr/client.py`:
  - [ ] Call `create_ibkr_order()` to get IBKR order and contract
  - [ ] Qualify the contract
  - [ ] Call `self.ib.placeOrder(contract, order)`
  - [ ] Extract trade object
  - [ ] Return order details dictionary:
    - [ ] order_id
    - [ ] status
    - [ ] filled
    - [ ] remaining
    - [ ] avg_fill_price
- [ ] Add pre-trade risk checks:
  - [ ] Call `IBKRRiskManager.validate_order()`
  - [ ] Reject orders that fail validation
  - [ ] Log rejection reason
- [ ] Implement order timeout handling
- [ ] Add comprehensive error handling
- [ ] Test placing MARKET orders
- [ ] Test placing LIMIT orders
- [ ] Test placing STOP orders
- [ ] Test order with invalid symbol
- [ ] Test order with insufficient funds

#### Cancel Order Implementation
- [ ] Implement `async def cancel_order()` in `src/brokers/ibkr/client.py`:
  - [ ] Accept order_id as parameter
  - [ ] Call `self.ib.cancelOrder(order_id)`
  - [ ] Handle cancellation errors
  - [ ] Return success/failure boolean
- [ ] Add order status check before cancellation
- [ ] Test cancelling open orders
- [ ] Test cancelling already filled orders
- [ ] Test cancelling non-existent order

#### Order Tracking Implementation
- [ ] Implement `async def get_orders()` in `src/brokers/ibkr/client.py`:
  - [ ] Accept status parameter ('open', 'filled', 'cancelled', 'all')
  - [ ] Get all trades from `self.ib.trades()`
  - [ ] Filter trades by status
  - [ ] Return list of order dictionaries:
    - [ ] order_id
    - [ ] symbol
    - [ ] action
    - [ ] quantity
    - [ ] status
    - [ ] filled
    - [ ] avg_fill_price
- [ ] Implement order status mapping:
  - [ ] PendingSubmit → 'pending'
  - [ ] PreSubmitted → 'presubmitted'
  - [ ] Submitted → 'open'
  - [ ] Filled → 'filled'
  - [ ] Cancelled → 'cancelled'
- [ ] Test retrieving open orders
- [ ] Test retrieving filled orders
- [ ] Test retrieving all orders

#### Order Event Handling
- [ ] Set up ib_insync event callbacks:
  - [ ] Register order status updates
  - [ ] Register fill events
  - [ ] Register error events
- [ ] Implement order update logging
- [ ] Store order history in database
- [ ] Test event handling during order execution

---

### Week 3: Portfolio & Account

#### Position Sync Implementation
- [ ] Implement `async def get_positions()` in `src/brokers/ibkr/positions.py`:
  - [ ] Get positions from `self.ib.positions()`
  - [ ] For each position:
    - [ ] Request market data for contract
    - [ ] Wait for price to arrive
    - [ ] Calculate market_value
    - [ ] Calculate unrealized_pnl
    - [ ] Create Position dataclass object
  - [ ] Return list of Position objects
- [ ] Handle missing market prices gracefully
- [ ] Filter out zero-quantity positions
- [ ] Test position retrieval
- [ ] Verify position calculations

#### Account Info Retrieval
- [ ] Implement `async def get_account()` in `src/brokers/ibkr/account.py`:
  - [ ] Get account values from `self.ib.accountValues()`
  - [ ] Convert to dictionary by tag
  - [ ] Extract key values:
    - [ ] CashBalance
    - [ ] NetLiquidation
    - [ ] BuyingPower
    - [ ] DayTradesRemaining
  - [ ] Create Account dataclass object
- [ ] Get account ID from `self.ib.managedAccounts()`
- [ ] Handle missing account values
- [ ] Test account info retrieval

#### Portfolio Summary Implementation
- [ ] Implement `async def get_portfolio_summary()`:
  - [ ] Call `get_account()` to get account info
  - [ ] Call `get_positions()` to get positions
  - [ ] Calculate invested_value
  - [ ] Calculate cash_percentage
  - [ ] Calculate total_pnl
  - [ ] Return summary dictionary:
    - [ ] total_value
    - [ ] cash_balance
    - [ ] invested_value
    - [ ] buying_power
    - [ ] open_positions
    - [ ] day_trades_remaining
- [ ] Test portfolio summary

#### Position Update Events
- [ ] Set up position update callbacks
- [ ] Track position changes in real-time
- [ ] Sync positions to database
- [ ] Test position update events

#### Account Update Events
- [ ] Set up account value update callbacks
- [ ] Track account changes in real-time
- [ ] Sync account data to database
- [ ] Test account update events

---

### Week 4: Market Data

#### Real-Time Data Streaming
- [ ] Create `IBKRMarketData` class in `src/brokers/ibkr/market_data.py`
- [ ] Implement `async def subscribe(symbol: str)`:
  - [ ] Create Stock contract for symbol
  - [ ] Qualify contract
  - [ ] Request market data with `reqMktData()`
  - [ ] Store ticker in _tickers dictionary
  - [ ] Return ticker object
- [ ] Implement `def get_quote(symbol: str)`:
  - [ ] Get ticker from _tickers
  - [ ] Return quote dictionary:
    - [ ] bid
    - [ ] ask
    - [ ] last
    - [ ] volume
    - [ ] high
    - [ ] low
    - [ ] close
    - [ ] time
- [ ] Implement `def unsubscribe(symbol: str)`:
  - [ ] Cancel market data subscription
  - [ ] Remove from _tickers
- [ ] Test subscribing to multiple symbols
- [ ] Test quote retrieval
- [ ] Test unsubscribing
- [ ] Handle subscription limits

#### Historical Data Retrieval
- [ ] Implement `async def get_historical_data()`:
  - [ ] Accept parameters:
    - [ ] symbol
    - [ ] duration (e.g., '1 D', '1 W', '1 M')
    - [ ] bar_size (e.g., '1 min', '5 min', '1 day')
    - [ ] what_to_show (TRADES, BID, ASK)
  - [ ] Create and qualify contract
  - [ ] Call `reqHistoricalDataAsync()`
  - [ ] Convert bars to list of dictionaries:
    - [ ] date
    - [ ] open
    - [ ] high
    - [ ] low
    - [ ] close
    - [ ] volume
  - [ ] Return list
- [ ] Test historical data retrieval for different timeframes
- [ ] Test with different bar sizes
- [ ] Handle data request limits

#### Market Data Manager
- [ ] Implement subscription management
- [ ] Track active subscriptions
- [ ] Handle connection recovery
- [ ] Implement data caching
- [ ] Add market data quality checks
- [ ] Implement subscription rotation (subscribe/unsubscribe as needed)

#### Data Integration
- [ ] Integrate with existing market data pipeline
- [ ] Store real-time data in TimescaleDB
- [ ] Store historical data in TimescaleDB
- [ ] Update existing indicators with IBKR data
- [ ] Test data quality and accuracy

---

### Week 5: TradeMind Integration

#### Broker Factory Implementation
- [ ] Implement `BrokerFactory` class in `src/execution/factory.py`:
  - [ ] Implement `@staticmethod create_broker(broker_type: str, config: dict)`:
    - [ ] Create IBKRBroker if type is 'ibkr'
    - [ ] Create PaperBroker if type is 'paper'
    - [ ] Raise ValueError for unknown types
  - [ ] Load broker configuration from config
  - [ ] Return broker instance
- [ ] Add broker type validation
- [ ] Test creating IBKR broker
- [ ] Test creating paper broker
- [ ] Test invalid broker type

#### Execution Router Implementation
- [ ] Implement `ExecutionRouter` class in `src/execution/router.py`:
  - [ ] Accept broker in `__init__`
  - [ ] Implement `async def execute_signal(signal: Dict)`:
    - [ ] Create Order object from signal
    - [ ] Call `broker.place_order()`
    - [ ] Return result
  - [ ] Add signal validation
  - [ ] Add error handling
- [ ] Implement `async def cancel_order(order_id: str)`
- [ ] Implement `async def get_portfolio_status()`
- [ ] Test execution with various signals
- [ ] Test error handling

#### Configuration Updates
- [ ] Update `src/config.py` with IBKR settings
- [ ] Add broker selection parameter to config
- [ ] Implement broker hot-switching capability
- [ ] Add broker configuration validation
- [ ] Document broker configuration options

#### Orchestrator Integration
- [ ] Update orchestrator to use ExecutionRouter
- [ ] Replace direct paper trading calls with broker interface
- [ ] Add broker-specific signal adaptation
- [ ] Update strategy execution flow
- [ ] Test full trading flow with IBKR broker

#### CLI Integration
- [ ] Add broker-related CLI commands:
  - [ ] `trademind broker status`
  - [ ] `trademind broker connect`
  - [ ] `trademind broker disconnect`
- [ ] Update portfolio commands to use broker
- [ ] Update trade commands to use broker
- [ ] Test CLI commands with IBKR broker

---

### Week 6: Testing & Validation

#### Unit Tests
- [ ] Create `tests/brokers/` directory
- [ ] Create `tests/brokers/__init__.py`
- [ ] Create `tests/brokers/test_ibkr_client.py`:
  - [ ] Test connection establishment
  - [ ] Test connection failure handling
  - [ ] Test disconnection
  - [ ] Test MARKET order placement
  - [ ] Test LIMIT order placement
  - [ ] Test STOP order placement
  - [ ] Test order cancellation
  - [ ] Test order retrieval
  - [ ] Test position retrieval
  - [ ] Test account info retrieval
- [ ] Create `tests/brokers/test_orders.py`:
  - [ ] Test order mapping
  - [ ] Test order validation
  - [ ] Test contract qualification
- [ ] Create `tests/brokers/test_market_data.py`:
  - [ ] Test symbol subscription
  - [ ] Test quote retrieval
  - [ ] Test unsubscription
  - [ ] Test historical data retrieval
- [ ] Create `tests/execution/test_factory.py`:
  - [ ] Test broker factory
- [ ] Create `tests/execution/test_router.py`:
  - [ ] Test execution router
- [ ] Achieve >80% code coverage
- [ ] Run all tests with pytest

#### Integration Tests
- [ ] Create `tests/brokers/test_integration.py`:
  - [ ] Test full order lifecycle (place, track, cancel)
  - [ ] Test position synchronization
  - [ ] Test account synchronization
  - [ ] Test market data streaming
  - [ ] Test error recovery
  - [ ] Test reconnection logic
- [ ] Test with live TWS/IB Gateway
- [ ] Test with offline TWS/IB Gateway
- [ ] Test with network interruptions
- [ ] Test concurrent order placement
- [ ] Test large order handling

#### Paper Trading Validation
- [ ] Run system on paper account for 1 week
- [ ] Execute at least 10 trades
- [ ] Verify all orders executed correctly
- [ ] Verify position tracking accuracy
- [ ] Verify account balance updates
- [ ] Verify P&L calculations
- [ ] Compare with TWS/IB Gateway data
- [ ] Document any discrepancies
- [ ] Fix identified issues

#### Performance Testing
- [ ] Test order placement latency
- [ ] Test market data latency
- [ ] Test concurrent connections
- [ ] Test memory usage under load
- [ ] Identify and fix performance bottlenecks

---

### Go-Live Preparation

#### Switch to Live Trading
- [ ] Verify all tests passing
- [ ] Complete successful paper trading week
- [ ] Review all documented issues
- [ ] Update config from port 7497 to 7496
- [ ] Test connection to live account (without trading)
- [ ] Verify account balance and permissions
- [ ] Create live trading backup of config
- [ ] Plan rollback procedure

#### Monitoring Setup
- [ ] Set up order status monitoring
- [ ] Set up position monitoring
- [ ] Set up account monitoring
- [ ] Set up connection monitoring
- [ ] Set up error tracking (Sentry or similar)
- [ ] Create monitoring dashboard
- [ ] Set up alert thresholds

#### Alert Configuration
- [ ] Configure connection failure alerts
- [ ] Configure order failure alerts
- [ ] Configure position limit alerts
- [ [ ] Configure loss limit alerts
- [ ] Configure system error alerts
- [ ] Test all alerts
- [ ] Set up notification channels (email, Slack, etc.)

#### Emergency Procedures
- [ ] Create emergency stop command
- [ ] Create position liquidation procedure
- [ ] Create system shutdown procedure
- [ ] Create manual override procedures
- [ ] Document emergency contacts
- [ ] Create incident response plan
- [ ] Test emergency stop procedure (on paper)

#### Runbook Creation
- [ ] Document daily operations
- [ ] Document weekly maintenance
- [ ] Document troubleshooting steps
- [ ] Document recovery procedures
- [ ] Document common issues and solutions
- [ ] Create on-call schedule

#### Pre-Go-Live Checklist
- [ ] All unit tests passing
- [ ] All integration tests passing
- [ ] Paper trading validation complete
- [ ] Monitoring configured and tested
- [ ] Alerts configured and tested
- [ ] Emergency procedures documented
- [ ] Runbook complete
- [ ] Team trained on procedures
- [ ] Backup procedures in place
- [ ] Regulatory compliance verified

---

### Risk Management Integration

#### Pre-Trade Checks
- [ ] Implement `IBKRRiskManager` class in `src/brokers/ibkr/risk_checks.py`:
  - [ ] `async def validate_order(self, order: Order) -> Tuple[bool, str]`
- [ ] Implement max order size check
- [ ] Implement max order value check
- [ ] Implement buying power check
- [ ] Implement day trade limit check
- [ ] Implement position size limit check
- [ ] Implement concentration limit check
- [ [ ] Implement volatility check
- [ ] Add all checks to order placement flow
- [ ] Test all risk checks

#### Risk Configuration
- [ ] Add risk parameters to `config/ibkr_config.yaml`:
  - [ ] max_order_size
  - [ ] max_order_value
  - [ ] max_position_size
  - [ ] max_sector_concentration
  - [ ] daily_loss_limit
  - [ ] volatility_threshold
- [ ] Load risk config in Settings
- [ ] Document all risk parameters

#### Safety Integration
- [ ] Integrate with existing Safety Circuit Breaker
- [ ] Add IBKR-specific safety rules
- [ ] Implement position-level stop-loss
- [ [ ] Implement portfolio-level stop-loss
- [ ] Test safety integration

#### Compliance Checks
- [ ] Implement pattern day trading rule checks
- [ ] Implement margin requirement checks
- [ ] Implement order size regulations
- [ ] Document compliance requirements

---

### Docker Deployment

#### IB Gateway Docker Setup
- [ ] Create `Dockerfile.ibkr`:
  - [ ] Use python:3.11-slim base image
  - [ ] Install system dependencies (xvfb, libxtst6, libxi6, libxrender1)
  - [ ] Download and install IB Gateway
  - [ ] Copy application code
  - [ ] Set up entry point
- [ ] Test IB Gateway Docker build
- [ ] Verify IB Gateway runs in container
- [ ] Configure IB Gateway for headless operation

#### Application Docker Setup
- [ ] Update existing `Dockerfile` for IBKR integration
- [ ] Add IBKR-specific dependencies
- [ ] Configure network for TWS/IB Gateway access
- [ ] Set up volume mounts for config
- [ ] Configure environment variables
- [ ] Test application Docker build

#### Docker Compose Configuration
- [ ] Create `docker-compose.yml`:
  - [ ] Service for IB Gateway
  - [ ] Service for TradeMind application
  - [ ] Service for TimescaleDB
  - [ ] Service for Redis
  - [ ] Network configuration
  - [ ] Volume configuration
- [ ] Configure health checks
- [ ] Configure restart policies
- [ ] Test full stack deployment

#### Production Deployment
- [ ] Set up production server
- [ ] Configure Docker daemon
- [ ] Set up SSL/TLS
- [ ] Configure firewall rules
- [ ] Set up log rotation
- [ ] Deploy production stack
- [ ] Verify all services running
- [ ] Test trading flow

#### Monitoring & Logging
- [ ] Set up centralized logging
- [ ] Configure log aggregation
- [ ] Set up metrics collection
- [ ] Create dashboards
- [ ] Set up alerting
- [ ] Test monitoring stack

---

### Documentation

#### Setup Documentation
- [ ] Create `docs/IBKR_SETUP.md`:
  - [ ] TWS/IB Gateway installation instructions
  - [ ] Paper account creation guide
  - [ ] API configuration steps
  - [ ] Connection troubleshooting
  - [ ] Common issues and solutions

#### API Documentation
- [ ] Document BaseBroker interface
- [ ] Document IBKRBroker methods
- [ ] Document Order, Position, Account dataclasses
- [ ] Document ExecutionRouter methods
- [ ] Add code examples

#### Configuration Documentation
- [ ] Document all IBKR config parameters
- [ ] Document risk management parameters
- [ ] Add example configurations
- [ ] Document environment variables

#### Deployment Documentation
- [ ] Document Docker deployment steps
- [ ] Document production setup
- [ [ ] Document monitoring setup
- [ ] Document emergency procedures
- [ ] Create deployment runbook

---

### Final Validation

#### End-to-End Testing
- [ ] Test complete trading workflow
- [ ] Test error recovery
- [ ] Test system restart
- [ ] Test backup/restore
- [ ] Load test system
- [ ] Validate all integrations

#### Sign-Off
- [ ] Code review complete
- [ ] Security review complete
- [ ] Performance review complete
- [ ] Documentation complete
- [ ] All stakeholders sign off
- [ ] Ready for production deployment

---

*Last Updated: 2026-02-07*  
*Based on: IBKR_INTEGRATION_PLAN.md*

---

## Shining Sun AI Trading Insights - Implementation Plan

*Created: 2026-02-08*  
*Based on: Shining Sun AI Trading Insights Review*

### Overview

This plan implements the advanced AI trading features from Shining Sun's insights, prioritizing features that provide the most value for TradeMind AI while building on the existing IBKR integration and multi-agent architecture.

### Priority Framework

- **High Priority**: Critical safety features, immediate trading edge, high ROI
- **Medium Priority**: Advanced features that significantly improve performance
- **Low Priority**: Nice-to-have enhancements, future capabilities

### Complexity Definitions

- **Simple**: 1-3 days, single file, minimal dependencies
- **Medium**: 1-2 weeks, multiple files, some new dependencies
- **Complex**: 3-4 weeks, architecture changes, significant testing

---

## Phase 1: Hallucination Hedge (High Priority, Medium Complexity)
*Timeline: Weeks 1-2*

### Critical Safety Layer - Validating All LLM Outputs

#### 1.1 Hard Data Validation Tool ✅
**Priority**: High  
**Complexity**: Simple  
**Dependencies**: None  
**Files**: `src/validation/hard_data_validator.py`, `src/validation/__init__.py`  
**Timeline**: 1-2 days

**Description**: Create a validation tool that cross-references all LLM-extracted numbers with actual market data from APIs.

**Implementation**:
- [ ] Create `HardDataValidator` class
- [ ] Implement `validate_price()` - Fetch real-time price from broker/yfinance
- [ ] Implement `validate_volume()` - Fetch real-time volume
- [ ] Implement `validate_indicator()` - Recalculate indicators from raw data
- [ ] Implement `validate_confidence()` - Ensure 0-1 range
- [ ] Add tolerance thresholds for validation (price +/- 1%, volume +/- 5%)
- [ ] Return validation result with warnings/errors
- [ ] Add logging for all validation attempts

**Acceptance Criteria**:
- Can validate prices against real-time data
- Flags discrepancies > threshold
- Returns detailed validation report

---

#### 1.2 Validation Middleware for Agents
**Priority**: High  
**Complexity**: Simple  
**Dependencies**: 1.1  
**Files**: `src/validation/middleware.py`, `src/agents/sentiment.py`, `src/agents/technical.py`  
**Timeline**: 1-2 days

**Description**: Wrap agent outputs with automatic validation before use.

**Implementation**:
- [ ] Create `@validate_output` decorator
- [ ] Apply to all agent `analyze()` methods
- [ ] On validation failure: log error, return HOLD signal, mark as invalid
- [ ] Add validation stats tracking (success rate, failure reasons)
- [ ] Implement fallback strategies when validation fails
- [ ] Add circuit breaker if validation fails > X% of time

**Acceptance Criteria**:
- All agent outputs validated before use
- Invalid outputs are rejected
- Fallback mechanisms work correctly

---

#### 1.3 Sentiment Agent Data Validation
**Priority**: High  
**Complexity**: Simple  
**Dependencies**: 1.1, 1.2  
**Files**: `src/agents/sentiment.py`  
**Timeline**: 1 day

**Description**: Validate sentiment agent's price/volume inputs and outputs.

**Implementation**:
- [ ] Validate price data before sending to LLM
- [ ] Validate volume data before sending to LLM
- [ ] Cross-check sentiment-derived prices with actual prices
- [ ] Flag suspicious sentiment patterns (e.g., bullish sentiment + falling price)
- [ ] Add price trend confirmation (sentiment must align with 1d trend)
- [ ] Add confidence penalties for mismatches

**Acceptance Criteria**:
- Input data validated before LLM call
- Output cross-referenced with actual market data
- Suspicious patterns flagged

---

#### 1.4 Orchestrator Validation Integration
**Priority**: High  
**Complexity**: Simple  
**Dependencies**: 1.2  
**Files**: `src/agents/orchestrator.py`  
**Timeline**: 1 day

**Description**: Integrate validation into the orchestrator's decision flow.

**Implementation**:
- [ ] Check validation status of each agent signal
- [ ] Down-weight signals from agents with validation failures
- [ ] Log validation warnings in decision reasoning
- [ ] Reject decisions if >50% of signals have validation issues
- [ ] Add validation status to API responses

**Acceptance Criteria**:
- Orchestrator considers validation status
- Invalid signals have reduced impact
- Validation status visible in UI

---

#### 1.5 Testing & Monitoring
**Priority**: High  
**Complexity**: Simple  
**Dependencies**: 1.1-1.4  
**Files**: `tests/validation/test_hard_data_validator.py`, `tests/validation/test_middleware.py`  
**Timeline**: 2-3 days

**Description**: Comprehensive tests and monitoring for validation layer.

**Implementation**:
- [ ] Unit tests for all validation functions
- [ ] Integration tests for validation middleware
- [ ] Mock API responses for test reliability
- [ ] Add validation metrics to monitoring dashboard
- [ ] Create alerts for high validation failure rates
- [ ] Log all validation failures with context
- [ ] Weekly validation report generation

**Acceptance Criteria**:
- 100% test coverage for validation logic
- Validation metrics tracked in dashboard
- Alerts configured for failures

---

## Phase 2: Multi-Agent Debate System (High Priority, Medium Complexity)
*Timeline: Weeks 3-5*

### Enhance Existing Agents with Debate Protocols

#### 2.1 Bull/Bear Agent Architecture
**Priority**: High  
**Complexity**: Medium  
**Dependencies**: None  
**Files**: `src/agents/bull.py`, `src/agents/bear.py`, `src/agents/debate.py`, `src/agents/judge.py`  
**Timeline**: 3-4 days

**Description**: Create specialized Bull and Bear agents that argue opposite sides, with a Judge to decide.

**Implementation**:
- [ ] Create `BullAgent` - Always looks for bullish signals
- [ ] Create `BearAgent` - Always looks for bearish signals
- [ ] Implement debate protocol:
  - [ ] Bull presents bullish case
  - [ ] Bear presents bearish case
  - [ ] Each agent critiques the other's arguments
  - [ ] Final round of rebuttals
- [ ] Create `JudgeAgent` - Evaluates both sides and decides
- [ ] Use LLM to generate arguments and critiques
- [ ] Implement structured debate format (arguments, evidence, counter-arguments)
- [ ] Add confidence scores for each argument
- [ ] Track debate history for learning

**Acceptance Criteria**:
- Bull/Bear agents generate coherent arguments
- Debate follows structured protocol
- Judge makes reasoned decisions

---

#### 2.2 Debate Integration with Existing Agents
**Priority**: High  
**Complexity**: Medium  
**Dependencies**: 2.1  
**Files**: `src/agents/orchestrator.py`, `src/agents/debate.py`  
**Timeline**: 2-3 days

**Description**: Integrate debate system into existing orchestrator.

**Implementation**:
- [ ] Add debate mode to orchestrator (optional, can toggle)
- [ ] For high-confidence signals: Run debate between Bull/Bear
- [ ] Feed existing Technical/Sentiment signals as evidence
- [ ] Judge's decision becomes final signal
- [ ] Add debate metadata to decision logging
- [ ] Include debate arguments in reasoning
- [ ] Configurable debate depth (number of rounds)
- [ ] Performance tracking: debate vs no-debate decisions

**Acceptance Criteria**:
- Debate mode works with existing agents
- Decisions include debate reasoning
- Performance metrics tracked

---

#### 2.3 Anti-Thesis Generator
**Priority**: Medium  
**Complexity**: Medium  
**Dependencies**: 2.1  
**Files**: `src/agents/antithesis.py`  
**Timeline**: 2-3 days

**Description**: LLM agent that builds strongest bear case for bullish positions (and vice versa).

**Implementation**:
- [ ] Create `AntiThesisAgent` class
- [ ] Input: Trading signal with reasoning
- [ ] Output: Strongest counter-arguments, risk factors, bear case
- [ ] Use prompt engineering to force alternative perspective
- [ ] Identify blind spots in analysis
- [ ] Suggest additional factors to consider
- [ ] Update confidence based on anti-thesis strength
- [ ] Flag high-risk decisions when anti-thesis is strong

**Acceptance Criteria**:
- Generates strong counter-arguments
- Identifies blind spots
- Reduces overconfidence bias

---

#### 2.4 Multi-Agent Crew with CrewAI
**Priority**: Medium  
**Complexity**: Complex  
**Dependencies**: None  
**Files**: `src/agents/crew.py`, `requirements.txt` (add crewai)  
**Timeline**: 4-5 days

**Description**: Implement full multi-agent crew system using CrewAI for complex workflows.

**Implementation**:
- [ ] Add `crewai>=0.28.0` to requirements.txt
- [ ] Create `ResearcherAgent` - Scans 10-Ks, 10-Qs, news
- [ ] Create `QuantAgent` - Pulls OHLC, calculates indicators
- [ ] Enhance `RiskAgent` - VaR, position limits
- [ ] Enhance `ExecutionerAgent` - Broker API interaction
- [ ] Define crew workflows:
  - [ ] Research workflow: Researcher → Quant → Risk
  - [ ] Trading workflow: Quant → Risk → Executioner
  - [ ] Analysis workflow: Researcher → Anti-Thesis → Judge
- [ ] Implement crew task orchestration
- [ ] Add crew performance monitoring
- [ ] Create crew dashboards

**Acceptance Criteria**:
- CrewAI integration works
- Multiple agents collaborate
- Workflows complete successfully

---

#### 2.5 Testing & Optimization
**Priority**: High  
**Complexity**: Medium  
**Dependencies**: 2.1-2.4  
**Files**: `tests/agents/test_debate.py`, `tests/agents/test_crew.py`  
**Timeline**: 3-4 days

**Description**: Test debate/crew systems and optimize performance.

**Implementation**:
- [ ] Unit tests for Bull/Bear agents
- [ ] Unit tests for Judge agent
- [ ] Integration tests for debate system
- [ ] Integration tests for crew workflows
- [ ] Backtesting: Debate vs No-Debate performance
- [ ] Optimize LLM prompts for better arguments
- [ ] Tune debate parameters (rounds, timeout)
- [ ] Performance benchmarking
- [ ] Cost analysis (API calls per decision)

**Acceptance Criteria**:
- All tests passing
- Debate improves decision quality
- Cost within acceptable limits

---

## Phase 3: Macro-Sentiment Analysis (Medium Priority, Medium Complexity)
*Timeline: Weeks 6-8*

### New Signal Source: Macro Economic Sentiment

#### 3.1 Macro Data Ingestion
**Priority**: Medium  
**Complexity**: Medium  
**Dependencies**: None  
**Files**: `src/data/macro_providers.py`, `src/agents/macro_sentiment.py`  
**Timeline**: 2-3 days

**Description**: Ingest macroeconomic data from multiple sources.

**Implementation**:
- [ ] Add `fredapi>=0.5.0` to requirements.txt (FRED data)
- [ ] Add `pandas-datareader>=0.10.0` to requirements.txt
- [ ] Create `MacroDataProvider` class
- [ ] Fetch FRED data (interest rates, GDP, unemployment)
- [ ] Fetch FOMC minutes (parse for sentiment)
- [ ] Fetch central bank speeches (parse for tone)
- [ ] Fetch global news headlines (Exa.ai or NewsAPI)
- [ ] Store macro data in database
- [ ] Implement update scheduling (daily for some, real-time for news)

**Acceptance Criteria**:
- Macro data successfully fetched
- Data stored in database
- Update scheduling works

---

#### 3.2 Macro Sentiment Analyzer
**Priority**: Medium  
**Complexity**: Medium  
**Dependencies**: 3.1  
**Files**: `src/agents/macro_sentiment.py`  
**Timeline**: 2-3 days

**Description**: Analyze macroeconomic sentiment using LLM.

**Implementation**:
- [ ] Create `MacroSentimentAgent` class
- [ ] Use LLM to analyze FOMC minutes tone (hawkish/dovish)
- [ ] Use LLM to analyze central bank speeches
- [ ] Use LLM to analyze global news sentiment
- [ ] Detect narrative shifts in economic outlook
- [ ] Generate macro sentiment score (-1 to +1)
- [ ] Identify key macro factors affecting markets
- [ ] Generate macro trading signals (risk-on, risk-off)
- [ ] Cache results (macro changes slowly, update every 12h)

**Acceptance Criteria**:
- Macro sentiment successfully analyzed
- Narrative shifts detected
- Signals generated

---

#### 3.3 Integration with Trading System
**Priority**: Medium  
**Complexity**: Simple  
**Dependencies**: 3.2  
**Files**: `src/agents/orchestrator.py`, `src/config.py`  
**Timeline**: 1-2 days

**Description**: Integrate macro sentiment into trading decisions.

**Implementation**:
- [ ] Add macro sentiment weight to config (default: 0.15)
- [ ] Integrate macro signal into orchestrator
- [ ] Macro sentiment modulates position sizing:
  - [ ] Risk-on (bullish macro): Increase position size 10-20%
  - [ ] Risk-off (bearish macro): Decrease position size 10-20%
- [ ] Macro sentiment affects sector allocation
- [ ] Add macro sentiment to decision reasoning
- [ ] Create macro sentiment dashboard widget
- [ ] Add macro sentiment to API responses

**Acceptance Criteria**:
- Macro sentiment integrated into decisions
- Position sizing adjusted appropriately
- Dashboard displays macro sentiment

---

#### 3.4 Narrative Shift Detection
**Priority**: Low  
**Complexity**: Medium  
**Dependencies**: 3.2  
**Files**: `src/agents/macro_sentiment.py`  
**Timeline**: 2-3 days

**Description**: Detect when market narrative shifts (before price action).

**Implementation**:
- [ ] Track macro sentiment history (last 6 months)
- [ ] Calculate sentiment momentum (rate of change)
- [ ] Detect sentiment reversals (bull → bear, bear → bull)
- [ ] Identify shift triggers (policy changes, events)
- [ ] Alert on narrative shifts
- [ ] Update strategy parameters based on new narrative
- [ ] Backtest: Trade on narrative shifts vs price action

**Acceptance Criteria**:
- Narrative shifts detected
- Alerts generated
- Shifts precede price action (backtest验证)

---

#### 3.5 Testing & Validation
**Priority**: Medium  
**Complexity**: Simple  
**Dependencies**: 3.1-3.4  
**Files**: `tests/agents/test_macro_sentiment.py`  
**Timeline**: 2 days

**Description**: Test macro sentiment system.

**Implementation**:
- [ ] Unit tests for macro data ingestion
- [ ] Unit tests for sentiment analysis
- [ ] Integration tests for trading system
- [ ] Backtest macro sentiment signals
- [ ] Validate narrative shift detection
- [ ] Performance benchmarking

**Acceptance Criteria**:
- All tests passing
- Macro sentiment improves performance
- Narrative shifts add value

---

## Phase 4: Advanced Options Strategies (Low Priority, High Complexity)
*Timeline: Weeks 9-13*

### Options Trading Framework

#### 4.1 Options Data Infrastructure
**Priority**: Low  
**Complexity**: Medium  
**Dependencies**: None  
**Files**: `src/data/options_providers.py`, `src/brokers/base.py` (extend)  
**Timeline**: 3-4 days

**Description**: Add options data capabilities to the system.

**Implementation**:
- [ ] Extend broker interface for options (greeks, chains)
- [ ] Add options data fetching from IBKR/yfinance
- [ ] Create `OptionsData` dataclass
- [ ] Implement IV (implied volatility) tracking
- [ ] Create options chain caching
- [ ] Store options data in database
- [ ] Create options data API endpoints

**Acceptance Criteria**:
- Options data successfully fetched
- Data stored and accessible via API

---

#### 4.2 Volatility Surface Analysis
**Priority**: Low  
**Complexity**: Complex  
**Dependencies**: 4.1  
**Files**: `src/strategies/volatility_surface.py`, `src/agents/volatility.py`  
**Timeline**: 4-5 days

**Description**: Monitor IV across sectors and alert on opportunities.

**Implementation**:
- [ ] Create `VolatilitySurfaceAnalyzer` class
- [ ] Calculate IV Rank by sector and expiration
- [ ] Identify when IV is "too cheap" (IVR < 25) or "too expensive" (IVR > 75)
- [ ] Monitor term structure (short-term vs long-term IV)
- [ ] Detect IV skew anomalies
- [ ] Generate volatility trading signals
- [ ] Create IV dashboard with sector comparison
- [ ] Add IV alerts to monitoring system

**Acceptance Criteria**:
- IV Rank calculated accurately
- Alerts generated for IV opportunities
- Dashboard displays volatility surface

---

#### 4.3 Zero-DTE Strategy Framework
**Priority**: Low  
**Complexity**: Complex  
**Dependencies**: 4.1  
**Files**: `src/strategies/zerodte.py`, `src/agents/zerodte_guardrails.py`  
**Timeline**: 5-6 days

**Description**: Implement Zero-DTE (Days to Expiration) options with guardrails.

**Implementation**:
- [ ] Create `ZeroDTEAgent` class
- [ ] Implement gamma exposure monitoring
- [ ] Define gamma flip zones (trigger hedge/close)
- [ ] Auto-trigger guards at gamma flips
- [ ] Position size limits for Zero-DTE
- [ ] Time-based liquidation (before close)
- [ ] Delta hedging logic
- [ ] Zero-DTE strategy templates (straddles, strangles, iron butterflies)
- [ ] Real-time P&L tracking for options positions

**Acceptance Criteria**:
- Gamma exposure tracked
- Guards trigger at flip zones
- Zero-DTE positions managed safely

---

#### 4.4 Strategy Optimization with LLM
**Priority**: Low  
**Complexity**: Medium  
**Dependencies**: 4.1  
**Files**: `src/agents/options_optimizer.py`  
**Timeline**: 3-4 days

**Description**: Use LLM to optimize options strategy parameters.

**Implementation**:
- [ ] Create `OptionsOptimizerAgent` class
- [ ] Input: Market outlook, IV Rank, delta constraints
- [ ] Use LLM to suggest optimal strategy parameters:
  - [ ] Iron Condor width and strikes
  - [ ] Calendar spread ratios
  - [ ] Diagonal spread selection
  - [ ] Risk/reward optimization
- [ ] Validate suggestions with backtesting
- [ ] Generate strategy recommendations
- [ ] Include reasoning and risk analysis

**Acceptance Criteria**:
- LLM generates reasonable strategy suggestions
- Suggestions validated by backtesting
- Recommendations improve performance

---

#### 4.5 Options Backtesting Engine
**Priority**: Low  
**Complexity**: Complex  
**Dependencies**: 4.1  
**Files**: `src/backtest/options_engine.py`  
**Timeline**: 5-6 days

**Description**: Enhance backtesting for options strategies.

**Implementation**:
- [ ] Extend backtesting engine for options
- [ ] Simulate options pricing (Black-Scholes, binomial)
- [ ] Model options assignment and exercise
- [ ] Simulate options decay (theta)
- [ ] Model Greeks (delta, gamma, theta, vega)
- [ ] Support multi-leg options strategies
- [ ] Options-specific metrics (win rate, avg return per day, max drawdown)
- [ ] Compare options vs stock performance

**Acceptance Criteria**:
- Options backtesting accurate
- Greeks modeled correctly
- Performance metrics valid

---

#### 4.6 Testing & Validation
**Priority**: Low  
**Complexity**: Medium  
**Dependencies**: 4.1-4.5  
**Files**: `tests/strategies/test_options.py`  
**Timeline**: 3-4 days

**Description**: Test options framework.

**Implementation**:
- [ ] Unit tests for options data
- [ ] Unit tests for volatility analysis
- [ ] Unit tests for Zero-DTE guardrails
- [ ] Integration tests for options trading
- [ ] Backtest validation: Compare simulated vs real options P&L
- [ ] Stress testing: Extreme volatility events
- [ ] Performance benchmarking

**Acceptance Criteria**:
- All tests passing
- Options framework reliable
- Backtesting accurate

---

## Phase 5: LangGraph Integration (Medium Priority, High Complexity)
*Timeline: Weeks 14-18*

### Advanced Workflow Orchestration

#### 5.1 LangGraph Setup
**Priority**: Medium  
**Complexity**: Medium  
**Dependencies**: None  
**Files**: `src/workflows/__init__.py`, `requirements.txt` (add langgraph)  
**Timeline**: 2-3 days

**Description**: Set up LangGraph for complex agent workflows.

**Implementation**:
- [ ] Add `langgraph>=0.0.20` to requirements.txt
- [ ] Create workflow directory structure
- [ ] Define LangGraph node types (agents, tools, conditions)
- [ ] Create base workflow templates
- [ ] Implement workflow state management
- [ ] Add workflow persistence (to database)
- [ ] Create workflow monitoring dashboard

**Acceptance Criteria**:
- LangGraph installed and configured
- Base workflow templates working
- State management operational

---

#### 5.2 Multi-Step Analysis Workflows
**Priority**: Medium  
**Complexity**: Complex  
**Dependencies**: 5.1  
**Files**: `src/workflows/analysis.py`  
**Timeline**: 4-5 days

**Description**: Create complex multi-step analysis workflows.

**Implementation**:
- [ ] Design comprehensive analysis workflow:
  - [ ] Step 1: Fetch data (Researcher)
  - [ ] Step 2: Technical analysis (Technical Agent)
  - [ ] Step 3: Sentiment analysis (Sentiment Agent)
  - [ ] Step 4: Macro analysis (Macro Agent)
  - [ ] Step 5: Risk assessment (Risk Agent)
  - [ ] Step 6: Debate (Bull vs Bear)
  - [ ] Step 7: Anti-thesis check
  - [ ] Step 8: Judge decision
  - [ ] Step 9: Validation (Hard Data)
  - [ ] Step 10: Final recommendation
- [ ] Implement workflow in LangGraph
- [ ] Add conditional branching based on intermediate results
- [ ] Implement workflow retry logic on failures
- [ ] Add workflow logging and debugging
- [ ] Create workflow visualization

**Acceptance Criteria**:
- Full analysis workflow works
- Conditional branching functional
- Workflow visualized

---

#### 5.3 Trading Decision Workflows
**Priority**: Medium  
**Complexity**: Complex  
**Dependencies**: 5.2  
**Files**: `src/workflows/trading.py`  
**Timeline**: 3-4 days

**Description**: Create workflows for trading decisions.

**Implementation**:
- [ ] Design trading decision workflow:
  - [ ] Check market conditions (pre-market)
  - [ ] Run analysis workflow (from 5.2)
  - [ ] Generate trading signals
  - [ ] Risk validation
  - [ ] Position sizing calculation
  - [ ] Order routing to broker
  - [ ] Execution confirmation
  - [ ] Post-trade analysis
- [ ] Implement in LangGraph
- [ ] Add safety checks at each step
- [ ] Implement circuit breaker integration
- [ ] Add workflow performance tracking
- [ ] Create workflow execution dashboard

**Acceptance Criteria**:
- Trading workflow complete
- Safety checks functional
- Dashboard operational

---

#### 5.4 Research & Learning Workflows
**Priority**: Low  
**Complexity**: Complex  
**Dependencies**: 5.1  
**Files**: `src/workflows/research.py`  
**Timeline**: 4-5 days

**Description**: Create workflows for research and continuous learning.

**Implementation**:
- [ ] Design research workflow:
  - [ ] Scan 10-K/10-Q filings (Researcher Agent)
  - [ ] Extract key metrics and guidance
  - [ ] Compare to historical guidance
  - [ ] Detect linguistic hedging (CEO tone)
  - [ ] Generate research reports
  - [ ] Update knowledge base
- [ ] Design learning workflow:
  - [ ] Analyze past trades
  - [ ] Identify success/failure patterns
  - [ ] Update agent weights
  - [ ] Tune strategy parameters
  - [ ] Generate performance reports
- [ ] Implement in LangGraph
- [ ] Schedule automated research (quarterly)
- [ ] Schedule learning reviews (weekly)
- [ ] Create research dashboard

**Acceptance Criteria**:
- Research workflows complete
- Learning workflows functional
- Automated scheduling works

---

#### 5.5 Workflow Orchestration & Management
**Priority**: Medium  
**Complexity**: Medium  
**Dependencies**: 5.1-5.4  
**Files**: `src/workflows/manager.py`, `src/api/routes/workflows.py`  
**Timeline**: 3-4 days

**Description**: Create workflow management system.

**Implementation**:
- [ ] Create `WorkflowManager` class
- [ ] Workflow scheduling and execution
- [ ] Workflow queue management
- [ ] Workflow status tracking
- [ ] Workflow history and logs
- [ ] Workflow performance metrics
- [ ] API endpoints for workflow management
- [ ] Manual workflow triggers
- [ ] Workflow configuration UI

**Acceptance Criteria**:
- Workflows managed centrally
- Status tracked accurately
- API endpoints functional

---

#### 5.6 Testing & Optimization
**Priority**: High  
**Complexity**: Medium  
**Dependencies**: 5.1-5.5  
**Files**: `tests/workflows/test_langgraph.py`  
**Timeline**: 3-4 days

**Description**: Test LangGraph workflows.

**Implementation**:
- [ ] Unit tests for workflow nodes
- [ ] Integration tests for workflows
- [ ] End-to-end workflow tests
- [ ] Workflow performance benchmarking
- [ ] Stress testing (concurrent workflows)
- [ ] Workflow failure recovery tests
- [ ] Cost optimization (minimize API calls)

**Acceptance Criteria**:
- All tests passing
- Workflows perform well
- Failure recovery works

---

## Phase 6: Advanced Backtesting (Medium Priority, Medium Complexity)
*Timeline: Weeks 19-21*

### VectorBT & QuantConnect Integration

#### 6.1 VectorBT Integration
**Priority**: Medium  
**Complexity**: Medium  
**Dependencies**: None  
**Files**: `src/backtest/vectorbt_engine.py`, `requirements.txt`  
**Timeline**: 2-3 days

**Description**: Integrate VectorBT for faster backtesting.

**Implementation**:
- [ ] Add `vectorbt>=0.25.0` to requirements.txt
- [ ] Create `VectorBTEngine` class
- [ ] Port existing strategies to VectorBT
- [ ] Implement vectorized backtesting
- [ ] Add VectorBT-specific metrics
- [ ] Compare VectorBT vs Backtrader results
- [ ] Document differences and use cases

**Acceptance Criteria**:
- VectorBT working
- Strategies ported
- Results validated

---

#### 6.2 QuantConnect Integration (Optional)
**Priority**: Low  
**Complexity**: Complex  
**Dependencies**: None  
**Files**: `src/backtest/quantconnect_engine.py`  
**Timeline**: 5-6 days

**Description**: Optional integration with QuantConnect for cloud backtesting.

**Implementation**:
- [ ] Research QuantConnect API
- [ ] Create QuantConnect adapter
- [ ] Port strategies to QuantConnect format
- [ ] Implement cloud backtesting
- [ ] Compare local vs cloud results
- [ ] Document advantages/disadvantages

**Acceptance Criteria**:
- QuantConnect integration working
- Strategies ported
- Results comparable

---

#### 6.3 Advanced Backtesting Features
**Priority**: Medium  
**Complexity**: Medium  
**Dependencies**: 6.1  
**Files**: `src/backtest/advanced_features.py`  
**Timeline**: 3-4 days

**Description**: Add advanced backtesting capabilities.

**Implementation**:
- [ ] Walk-forward analysis (rolling backtests)
- [ ] Parameter optimization (grid search, genetic algorithms)
- [ ] Monte Carlo simulations for risk assessment
- [ ] Multi-asset backtesting
- [ ] Portfolio backtesting (multiple strategies)
- [ ] Transaction cost modeling improvements
- [ ] Market impact modeling
- [ ] Regime detection backtesting

**Acceptance Criteria**:
- Advanced features working
- Optimization results meaningful
- Risk assessment accurate

---

#### 6.4 Backtesting Validation
**Priority**: High  
**Complexity**: Simple  
**Dependencies**: 6.1-6.3  
**Files**: `tests/backtest/test_vectorbt.py`  
**Timeline**: 2-3 days

**Description**: Validate backtesting engines.

**Implementation**:
- [ ] Cross-validate VectorBT vs Backtrader
- [ ] Validate parameter optimization results
- [ ] Monte Carlo validation against historical worst cases
- [ ] Walk-forward analysis validation
- [ ] Create backtesting accuracy metrics

**Acceptance Criteria**:
- Engines produce similar results
- Optimization validated
- Risk metrics accurate

---

## Phase 7: Production Readiness & Monitoring (High Priority, Simple-Medium)
*Timeline: Weeks 22-24*

### Final Production Preparation

#### 7.1 Comprehensive Monitoring Dashboard
**Priority**: High  
**Complexity**: Medium  
**Dependencies**: All previous phases  
**Files**: `src/api/monitoring.py`, `src/api/templates/monitoring.html`  
**Timeline**: 3-4 days

**Description**: Create comprehensive monitoring dashboard.

**Implementation**:
- [ ] Real-time portfolio monitoring
- [ ] Agent activity tracking (all agents)
- [ ] Workflow status monitoring
- [ ] Validation failure alerts
- [ ] Macro sentiment display
- [ ] Volatility surface visualization
- [ ] Options positions monitoring
- [ ] Performance metrics dashboard
- [ ] System health checks
- [ ] Alert configuration UI

**Acceptance Criteria**:
- All metrics visible
- Real-time updates working
- Alerts functional

---

#### 7.2 Alert System Enhancement
**Priority**: High  
**Complexity**: Simple  
**Dependencies**: All previous phases  
**Files**: `src/core/alert_manager.py`  
**Timeline**: 2-3 days

**Description**: Enhance alert system for new features.

**Implementation**:
- [ ] Validation failure alerts
- [ ] Debate conflict alerts (Bull/Bear strongly disagree)
- [ ] Narrative shift alerts
- [ ] IV anomaly alerts
- [ ] Zero-DTE guardrail triggers
- [ ] Workflow failure alerts
- [ ] Multi-channel notifications (email, Slack, Discord)
- [ ] Alert history and analytics
- [ ] Alert escalation rules

**Acceptance Criteria**:
- All new features have alerts
- Multi-channel notifications work
- Alert history tracked

---

#### 7.3 Performance Optimization
**Priority**: High  
**Complexity**: Medium  
**Dependencies**: All previous phases  
**Files**: Various  
**Timeline**: 3-4 days

**Description**: Optimize system performance.

**Implementation**:
- [ ] LLM call optimization (batching, caching)
- [ ] Workflow execution optimization
- [ ] Database query optimization
- [ ] API response time optimization
- [ ] Memory usage optimization
- [ ] Concurrency improvements
- [ ] Load testing and benchmarking
- [ ] Performance profiling
- [ ] Documentation of performance characteristics

**Acceptance Criteria**:
- System responsive under load
- API response times < 1s
- Memory usage stable

---

#### 7.4 Documentation & Training
**Priority**: High  
**Complexity**: Simple  
**Dependencies**: All previous phases  
**Files**: `docs/`, `README.md` updates  
**Timeline**: 2-3 days

**Description**: Document new features and create training materials.

**Implementation**:
- [ ] Update README with new features
- [ ] Create API documentation for new endpoints
- [ ] Create user guide for new features
- [ ] Create admin guide for monitoring
- [ ] Document configuration options
- [ ] Create troubleshooting guide
- [ ] Create video tutorials (optional)
- [ ] Create onboarding checklist

**Acceptance Criteria**:
- All features documented
- User guide complete
- Troubleshooting guide useful

---

#### 7.5 Go-Live Checklist & Sign-Off
**Priority**: High  
**Complexity**: Simple  
**Dependencies**: All previous phases  
**Files**: `docs/GO_LIVE_CHECKLIST.md`  
**Timeline**: 1-2 days

**Description**: Create comprehensive go-live checklist.

**Implementation**:
- [ ] Create detailed go-live checklist
- [ ] Include all safety checks
- [ ] Include monitoring setup
- [ ] Include rollback procedures
- [ ] Include emergency contacts
- [ ] Performance baselines documented
- [ ] Stakeholder sign-off process
- [ ] Post-go-live monitoring plan

**Acceptance Criteria**:
- Checklist comprehensive
- All items checked
- Stakeholders signed off

---

## Summary & Recommendations

### Critical Path (Do First)
1. **Phase 1: Hallucination Hedge** (Weeks 1-2) - Critical safety
2. **Phase 2: Multi-Agent Debate System** (Weeks 3-5) - High value

### High Value (Do Soon)
3. **Phase 3: Macro-Sentiment Analysis** (Weeks 6-8) - New signal source
4. **Phase 7: Production Readiness** (Weeks 22-24) - Essential for deployment

### Future Growth (Do Later)
5. **Phase 5: LangGraph Integration** (Weeks 14-18) - Advanced workflows
6. **Phase 4: Advanced Options** (Weeks 9-13) - Future capability
7. **Phase 6: Advanced Backtesting** (Weeks 19-21) - Performance analysis

### Timeline Summary
- **Weeks 1-2**: Safety foundation (Hallucination Hedge)
- **Weeks 3-5**: Enhanced decision making (Debate System)
- **Weeks 6-8**: New signal source (Macro Sentiment)
- **Weeks 9-13**: Options capabilities (can start later)
- **Weeks 14-18**: Advanced workflows (LangGraph)
- **Weeks 19-21**: Advanced backtesting
- **Weeks 22-24**: Production readiness

### Total Estimated Timeline
- **Minimum Viable**: Phases 1-2, 7 (8 weeks)
- **Full Implementation**: All phases (24 weeks / 6 months)

### Key Dependencies
- Hallucination Hedge (Phase 1) must be first
- All other phases can proceed in parallel after Phase 1
- Production readiness (Phase 7) depends on all feature phases

### Resource Requirements
- **Development**: 1-2 developers
- **AI/LLM Costs**: $200-500/month (depending on usage)
- **Data APIs**: Free tiers sufficient for start, may need paid later
- **Infrastructure**: Existing infrastructure sufficient

---

## Second Review & Recommendations

### Strengths of This Plan

1. **Safety First**: Hallucination Hedge is critical and prioritized first
2. **Builds on Existing Foundation**: Leverages current IBKR integration and agents
3. **Incremental Value**: Each phase provides immediate value
4. **Clear Priorities**: High/Medium/Low framework is well-defined
5. **Realistic Timelines**: Complex features allocated appropriate time

### Potential Improvements

1. **Add Risk Analysis**: Each phase should include risk assessment
2. **Add Cost Analysis**: Estimate API costs for LLM calls
3. **Add Success Metrics**: Define measurable outcomes for each phase
4. **Add Rollback Criteria**: When to abandon a phase if not working
5. **Add A/B Testing**: Validate new features against baseline

### Missing Considerations

1. **Data Privacy**: Ensure macro data and news sources comply with terms of service
2. **Regulatory Compliance**: Options trading has additional regulations
3. **Model Drift**: LLM behavior can change over time, need monitoring
4. **API Rate Limits**: Plan for rate limits on data sources
5. **Disaster Recovery**: What if a workflow gets stuck in infinite loop?

### Recommended Additions

1. **Add Phase 0: Risk Assessment & Planning**
   - Risk matrix for each phase
   - Cost-benefit analysis
   - Success criteria definition
   - Rollback procedures

2. **Add Continuous Integration Improvements**
   - Automated testing for all new features
   - Code quality gates (linting, type checking)
   - Performance regression testing

3. **Add Documentation Improvements**
   - Architecture diagrams for each phase
   - API documentation auto-generation
   - Decision logs for architectural choices

4. **Add Performance Budget**
   - Max LLM calls per day
   - Max API response time
   - Max memory usage

5. **Add Feature Flags**
   - Ability to enable/disable features without code deployment
   - Gradual rollout of new features
   - A/B testing capabilities

### Final Recommendation

**Proceed with Phase 1 (Hallucination Hedge) immediately.** This is the most critical safety feature and provides immediate value.

**Then implement Phase 2 (Debate System)** as it significantly enhances the existing agent system.

**Evaluate results after Phase 2** before committing to full 6-month timeline. If early phases show strong value, continue. If not, reassess priorities.

The plan is solid, well-structured, and builds appropriately on the existing TradeMind AI foundation.

---

*Plan Created: 2026-02-08*  
*Total Estimated Timeline: 6 months (24 weeks) for full implementation*  
*Minimum Viable: 8 weeks (Phases 1, 2, 7)*


---

## LangGraph Migration Tasks (New Priority)

### Phase 1: Foundation (Week 1)

#### L1. Install Dependencies
- [ ] Install langgraph>=1.0.8
- [ ] Install langchain-core, langchain-community
- [ ] Update requirements.txt

#### L2. Create Directory Structure
- [ ] Create src/langgraph/ directory
- [ ] Create state.py (TradingState schema)
- [ ] Create graph.py (graph construction)
- [ ] Create nodes/ subdirectory
- [ ] Create persistence.py (checkpointer config)

#### L3. Define TradingState
- [ ] Define TypedDict for state
- [ ] Add all required fields
- [ ] Add type annotations
- [ ] Add state validation

#### L4. Create Basic Graph Skeleton
- [ ] Import StateGraph, START, END
- [ ] Add placeholder nodes
- [ ] Add linear edges
- [ ] Compile with checkpointer
- [ ] Test basic execution

#### L5. Add Persistence Layer
- [ ] Configure SqliteSaver
- [ ] Set up database file
- [ ] Test checkpoint/save
- [ ] Test restore/resume

#### L6. Set Up LangSmith (Optional)
- [ ] Enable LANGSMITH_TRACING
- [ ] Add API key to .env
- [ ] Test trace visibility
- [ ] Create evaluation runs

---

### Phase 2: Agent Migration (Week 2)

#### L7. Technical Agent Migration
- [ ] Create analysis_nodes.py
- [ ] Implement technical_analysis() node
- [ ] Preserve existing logic
- [ ] Return state updates
- [ ] Add tests

#### L8. Sentiment Agent Migration
- [ ] Implement sentiment_analysis() node
- [ ] Preserve caching
- [ ] Add error handling
- [ ] Add tests

#### L9. Risk Manager Migration
- [ ] Implement risk_assessment() node
- [ ] Integrate IBKRRiskManager
- [ ] Add veto logic
- [ ] Calculate position sizing
- [ ] Add tests

#### L10. Orchestrator Migration
- [ ] Implement make_decision() node
- [ ] Weighted voting logic
- [ ] Confidence aggregation
- [ ] Decision routing
- [ ] Add tests

#### L11. Create Base Node Templates
- [ ] Create node_base.py
- [ ] Add error handling decorator
- [ ] Add logging helpers
- [ ] Add state update helpers

---

### Phase 3: Advanced Features (Week 3)

#### L12. Create Debate Agents
- [ ] Create src/agents/debate.py
- [ ] Implement BullAgent
- [ ] Implement BearAgent
- [ ] Implement JudgeAgent
- [ ] Add LLM argument generation

#### L13. Debate Protocol Node
- [ ] Implement debate_protocol() node
- [ ] Present cases logic
- [ ] Cross-examination logic
- [ ] Final verdict logic
- [ ] Track debate history

#### L14. Conditional Edges
- [ ] Implement should_debate()
- [ ] Implement should_review()
- [ ] Implement should_execute()
- [ ] Implement should_retry()
- [ ] Add edges to graph
- [ ] Test all paths

#### L15. Human-in-the-Loop
- [ ] Implement human_review() node
- [ ] Add interrupt logic
- [ ] Create approval API endpoint
- [ ] Add notification hooks
- [ ] Add tests

#### L16. Memory Implementation
- [ ] Add short-term memory (messages)
- [ ] Add long-term memory (DB)
- [ ] Implement state versioning
- [ ] Add retrieval logic
- [ ] Tests

---

### Phase 4: Integration & Testing (Week 4)

#### L17. Execute Trade Node
- [ ] Implement execute_trade() node
- [ ] Connect SignalExecutor
- [ ] Add error handling
- [ ] Track order status
- [ ] Add tests

#### L18. End-to-End Tests
- [ ] Test BUY scenario
- [ ] Test SELL scenario
- [ ] Test HOLD scenario
- [ ] Test debate flow
- [ ] Test human approval flow
- [ ] Test veto flow
- [ ] Test retry/loop

#### L19. IBKR Integration Tests
- [ ] Test connection
- [ ] Test order placement
- [ ] Test order cancellation
- [ ] Test position sync
- [ ] Test error handling

#### L20. Performance Tests
- [ ] Measure execution time
- [ ] Test concurrent workflows
- [ ] Test with many symbols
- [ ] Memory profiling
- [ ] Optimization

#### L21. Backtesting Comparison
- [ ] Run backtest with LangGraph
- [ ] Compare to baseline
- [ ] Measure performance
- [ ] Document results
- [ ] A/B testing

#### L22. Documentation
- [ ] Update README
- [ ] Create migration guide
- [ ] API documentation
- [ ] Architecture diagrams
- [ ] Training materials

---

### Post-Migration Tasks

#### L23. Monitoring & Observability
- [ ] Set up dashboards
- [ ] Configure alerts
- [ ] Log key metrics
- [ ] Create incident response plan

#### L24. Gradual Rollout
- [ ] Feature flag implementation
- [ ] 10% traffic test
- [ ] 50% traffic test
- [ ] Full rollout
- [ ] Monitor metrics

#### L25. Performance Optimization
- [ ] Profile hot paths
- [ ] Optimize state updates
- [ ] Cache frequently accessed data
- [ ] Reduce memory usage
- [ ] Improve streaming

---

*Last Updated: 2026-02-08*
*Based on: LANGGRAPH_MIGRATION_PLAN.md*


---

## NEW: Market-Wide Analysis Features (High Priority)

### Phase X: Market Mood Detection

**Status:** ⏳ PENDING IMPLEMENTATION  
**Priority:** High  
**Complexity:** Medium  
**ETA:** Post-market hours today

#### X.1 VIX Fear Index Monitor
**Files:** `src/market_indicators/vix_monitor.py`, `src/agents/market_mood.py`  
**Description:** Monitor VIX (Volatility Index) as market fear gauge.

**Tasks:**
- [ ] Create `VIXMonitor` class
- [ ] Fetch VIX data from Yahoo Finance
- [ ] Calculate VIX trend (rising/falling)
- [ ] Define fear levels:
  - VIX < 20: Low fear (greed)
  - VIX 20-25: Normal
  - VIX 25-30: Elevated fear
  - VIX > 30: High fear (panic)
- [ ] Generate market mood signal (risk-on/risk-off)
- [ ] Cache VIX data (update every 15 min)
- [ ] Add VIX to watchlist by default

**Success Criteria:**
```python
vix = VIXMonitor()
mood = await vix.get_market_mood()
# Returns: {"level": "high_fear", "vix": 32.5, "signal": "risk_off"}
```

#### X.2 Market Breadth Analysis
**Files:** `src/market_indicators/breadth_monitor.py`  
**Description:** Track advance/decline ratio for market health.

**Tasks:**
- [ ] Create `MarketBreadthMonitor` class
- [ ] Fetch NYSE advance/decline data
- [ ] Calculate:
  - Advance/Decline Ratio
  - Advance/Decline Line
  - % of stocks above 50-day MA
  - % of stocks above 200-day MA
- [ ] Generate breadth score (0-100)
- [ ] Define breadth signals:
  - Score > 70: Strong breadth (bullish)
  - Score 40-70: Neutral
  - Score < 40: Weak breadth (bearish)
- [ ] Store breadth history
- [ ] Display on dashboard

**Success Criteria:**
```python
breadth = await breadth_monitor.get_breadth_score()
# Returns: {"score": 65, "ad_ratio": 1.8, "above_50ma": 58, "signal": "neutral"}
```

#### X.3 CNN Fear & Greed Index Integration
**Files:** `src/market_indicators/fear_greed.py`  
**Description:** Scrape or API fetch CNN Fear & Greed Index.

**Tasks:**
- [ ] Create `FearGreedMonitor` class
- [ ] Fetch Fear & Greed Index value
- [ ] Parse components:
  - Market Momentum
  - Stock Price Strength
  - Stock Price Breadth
  - Put/Call Ratio
  - Market Volatility (VIX)
  - Safe Haven Demand
  - Junk Bond Demand
- [ ] Map index to mood:
  - 0-25: Extreme Fear
  - 26-40: Fear
  - 41-60: Neutral
  - 61-75: Greed
  - 76-100: Extreme Greed
- [ ] Generate trading signal
- [ ] Cache results (update daily)

**Success Criteria:**
```python
fg = FearGreedMonitor()
index = await fg.get_index()
# Returns: {"value": 45, "mood": "neutral", "signal": "hold"}
```

#### X.4 Market Mood Agent
**Files:** `src/agents/market_mood.py`  
**Description:** Combine all market-wide indicators into unified mood signal.

**Tasks:**
- [ ] Create `MarketMoodAgent` class (extends BaseAgent)
- [ ] Aggregate inputs:
  - VIX level (30% weight)
  - Market breadth (30% weight)
  - Fear & Greed Index (20% weight)
  - Sector performance (20% weight)
- [ ] Calculate composite mood score (-1 to +1)
- [ ] Generate signals:
  - Strong Bullish (>0.6): Risk-on, increase exposure
  - Bullish (0.2 to 0.6): Normal trading
  - Neutral (-0.2 to 0.2): Cautious
  - Bearish (-0.6 to -0.2): Reduce exposure
  - Strong Bearish (<-0.6): Risk-off, go to cash
- [ ] Integrate with RiskAgent
- [ ] Display mood on dashboard

**Success Criteria:**
```python
agent = MarketMoodAgent()
signal = await agent.analyze()
# Returns: AgentSignal(decision="risk_on", confidence=0.75, mood="bullish")
```

---

### Phase Y: Sector Rotation Tracking

**Status:** ⏳ PENDING IMPLEMENTATION  
**Priority:** High  
**Complexity:** Medium  
**ETA:** Post-market hours today

#### Y.1 Sector Performance Monitor
**Files:** `src/market_indicators/sector_performance.py`  
**Description:** Track relative performance of all market sectors.

**Tasks:**
- [ ] Create `SectorPerformanceMonitor` class
- [ ] Define sector ETFs to track:
  - XLK (Technology)
  - XLF (Financials)
  - XLE (Energy)
  - XLU (Utilities)
  - XLI (Industrials)
  - XLP (Consumer Staples)
  - XLY (Consumer Discretionary)
  - XLB (Materials)
  - XLC (Communication)
  - XLRE (Real Estate)
  - XBI (Biotech)
  - XRT (Retail)
- [ ] Calculate performance metrics:
  - 1-day return
  - 5-day return
  - 1-month return
  - YTD return
  - Relative strength vs SPY
- [ ] Rank sectors by performance
- [ ] Identify top 3 and bottom 3 sectors
- [ ] Store sector performance history

**Success Criteria:**
```python
sectors = SectorPerformanceMonitor()
performance = await sectors.get_performance()
# Returns: [
#   {"sector": "Technology", "etf": "XLK", "1d": 2.1, "1m": 8.5, "rank": 1},
#   {"sector": "Energy", "etf": "XLE", "1d": -1.2, "1m": -3.2, "rank": 11}
# ]
```

#### Y.2 Sector Rotation Detector
**Files:** `src/market_indicators/sector_rotation.py`  
**Description:** Detect money flow between sectors (rotation signals).

**Tasks:**
- [ ] Create `SectorRotationDetector` class
- [ ] Calculate momentum for each sector:
  - Price momentum (10-day vs 50-day)
  - Relative strength vs S&P 500
  - Volume momentum
- [ ] Detect rotation patterns:
  - Growth → Value
  - Tech → Energy
  - Cyclicals → Defensives
  - Risk-on → Risk-off
- [ ] Generate rotation signals:
  - "Money flowing INTO [sector]"
  - "Money flowing OUT OF [sector]"
  - "Rotation from [sector A] to [sector B]"
- [ ] Track rotation strength (0-100)
- [ ] Historical rotation analysis

**Success Criteria:**
```python
rotation = SectorRotationDetector()
signals = await rotation.get_signals()
# Returns: [
#   {"type": "inflow", "sector": "Energy", "strength": 75, "signal": "strong_buy"},
#   {"type": "outflow", "sector": "Technology", "strength": 60, "signal": "weak_hold"}
# ]
```

#### Y.3 Sector Momentum Scoring
**Files:** `src/market_indicators/sector_momentum.py`  
**Description:** Calculate composite momentum score for each sector.

**Tasks:**
- [ ] Create `SectorMomentumScorer` class
- [ ] Calculate momentum components:
  - Price momentum (30%)
  - Volume momentum (20%)
  - Relative strength (30%)
  - Trend alignment (20%)
- [ ] Score range: -100 (strong downtrend) to +100 (strong uptrend)
- [ ] Categorize sectors:
  - Leading (+50 to +100): Strong uptrend
  - Improving (+20 to +50): Getting stronger
  - Neutral (-20 to +20): Sideways
  - Weakening (-50 to -20): Getting weaker
  - Lagging (-100 to -50): Strong downtrend
- [ ] Generate sector allocation recommendations
- [ ] Update daily

**Success Criteria:**
```python
scorer = SectorMomentumScorer()
scores = await scorer.get_scores()
# Returns: {
#   "Technology": {"score": 65, "category": "leading", "recommendation": "overweight"},
#   "Energy": {"score": -45, "category": "weakening", "recommendation": "underweight"}
# }
```

#### Y.4 Sector Rotation Agent
**Files:** `src/agents/sector_rotation.py`  
**Description:** Make trading decisions based on sector rotation.

**Tasks:**
- [ ] Create `SectorRotationAgent` class (extends BaseAgent)
- [ ] Analyze sector rotation data
- [ ] Generate signals:
  - "Buy [sector ETF] - rotation in progress"
  - "Sell [sector ETF] - rotation out"
  - "Avoid [sector] - lagging momentum"
  - "Focus on [sector] - leading momentum"
- [ ] Recommend top 3 sectors to buy
- [ ] Recommend top 3 sectors to avoid
- [ ] Weight recommendations by rotation strength
- [ ] Integrate with portfolio manager
- [ ] Display sector allocation on dashboard

**Success Criteria:**
```python
agent = SectorRotationAgent()
signal = await agent.analyze()
# Returns: AgentSignal(
#   decision="rotate",
#   confidence=0.82,
#   reasoning="Strong rotation from Tech to Energy",
#   data={"buy_sectors": ["XLE", "XLF"], "sell_sectors": ["XLK"]}
# )
```

#### Y.5 Sector-Aware Auto-Trader
**Files:** `auto_trader.py` (update)  
**Description:** Enhance auto-trader with sector rotation awareness.

**Tasks:**
- [ ] Integrate SectorRotationAgent
- [ ] Filter watchlist by top-performing sectors
- [ ] Prefer stocks in leading sectors
- [ ] Avoid stocks in lagging sectors
- [ ] Log sector allocation
- [ ] Display sector rotation status

**Success Criteria:**
```
Auto-trader selects stocks from top 3 sectors only
Avoids bottom 3 sectors completely
Logs: "Selecting AAPL from Technology (Leading sector)"
```

---

### Integration Checklist

- [ ] Add MarketMoodAgent to multi-agent system
- [ ] Add SectorRotationAgent to multi-agent system
- [ ] Update dashboard to show market mood
- [ ] Update dashboard to show sector performance
- [ ] Add sector allocation pie chart
- [ ] Add VIX indicator to header
- [ ] Add Fear & Greed index widget
- [ ] Test all new features with paper trading
- [ ] Document new APIs
- [ ] Update README with new features

