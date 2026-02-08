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
