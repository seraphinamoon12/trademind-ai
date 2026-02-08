# TradeMind AI - LLM API Documentation

## API Schema

```yaml
openapi: 3.0.0
info:
  title: TradeMind AI API
  version: 1.0.0
  description: Algorithmic trading agent API for swing trading

servers:
  - url: http://localhost:8000
    description: Local development

components:
  schemas:
    
    # Portfolio
    Portfolio:
      type: object
      properties:
        total_value: {type: number, example: 102456.78}
        cash_balance: {type: number, example: 45000.00}
        invested_value: {type: number, example: 57456.78}
        daily_pnl: {type: number, example: 234.56}
        daily_pnl_pct: {type: number, example: 0.23}
        total_return: {type: number, example: 2456.78}
        total_return_pct: {type: number, example: 2.46}
        open_positions: {type: integer, example: 3}
        portfolio_heat: {type: number, example: 4.2}
    
    Holding:
      type: object
      properties:
        symbol: {type: string, example: "AAPL"}
        quantity: {type: integer, example: 100}
        avg_cost: {type: number, example: 150.50}
        current_price: {type: number, example: 155.20}
        market_value: {type: number, example: 15520.00}
        unrealized_pnl: {type: number, example: 470.00}
        unrealized_pnl_pct: {type: number, example: 3.12}
    
    # Trades
    Trade:
      type: object
      properties:
        id: {type: integer, example: 1042}
        symbol: {type: string, example: "AAPL"}
        action: {type: string, enum: [BUY, SELL], example: "BUY"}
        quantity: {type: integer, example: 100}
        price: {type: number, example: 150.50}
        total_value: {type: number, example: 15050.00}
        timestamp: {type: string, format: date-time}
        strategy: {type: string, example: "rsi_reversion"}
        reasoning: {type: string}
        confidence: {type: number, example: 0.72}
        transaction_costs: {type: number, example: 15.05}
    
    # Strategies
    Strategy:
      type: object
      properties:
        name: {type: string, example: "rsi_reversion"}
        enabled: {type: boolean, example: true}
        total_trades: {type: integer, example: 156}
        winning_trades: {type: integer, example: 66}
        losing_trades: {type: integer, example: 90}
        win_rate: {type: number, example: 0.423}
        profit_factor: {type: number, example: 1.45}
        gross_profit: {type: number, example: 12345.67}
        gross_loss: {type: number, example: -8514.21}
    
    Signal:
      type: object
      properties:
        symbol: {type: string, example: "AAPL"}
        strategy: {type: string, example: "rsi_reversion"}
        signal: {type: string, enum: [BUY, SELL, HOLD], example: "BUY"}
        confidence: {type: number, example: 0.72}
        price: {type: number, example: 155.20}
        timestamp: {type: string, format: date-time}
        indicators: {type: object}
    
    # Safety
    SafetyStatus:
      type: object
      properties:
        circuit_breaker_armed: {type: boolean, example: true}
        circuit_breaker_triggered: {type: boolean, example: false}
        trading_allowed: {type: boolean, example: true}
        daily_pnl_pct: {type: number, example: 0.23}
        current_drawdown_pct: {type: number, example: 2.1}
        consecutive_losses: {type: integer, example: 1}
        max_open_positions: {type: integer, example: 5}
        current_open_positions: {type: integer, example: 3}
        portfolio_heat_pct: {type: number, example: 4.2}
    
    CircuitBreakerStatus:
      type: object
      properties:
        is_halted: {type: boolean, example: false}
        halt_reason: {type: string, nullable: true}
        halt_time: {type: string, format: date-time, nullable: true}
        daily_loss_limit_pct: {type: number, example: 0.03}
        warning_drawdown_pct: {type: number, example: 0.10}
        max_drawdown_pct: {type: number, example: 0.15}
        consecutive_loss_limit: {type: integer, example: 5}
    
    PortfolioHeat:
      type: object
      properties:
        current_heat_pct: {type: number, example: 4.2}
        max_heat_pct: {type: number, example: 10.0}
        risk_amount: {type: number, example: 4200.00}
        max_risk_amount: {type: number, example: 10000.00}
        positions: {type: array, items: {type: object}}
    
    # Config
    Config:
      type: object
      properties:
        # Trading
        starting_capital: {type: number, default: 100000.00}
        max_position_pct: {type: number, default: 0.10}
        max_daily_loss_pct: {type: number, default: 0.03}
        stop_loss_pct: {type: number, default: 0.05}
        take_profit_pct: {type: number, default: 0.10}
        check_interval_minutes: {type: integer, default: 15}
        trading_start: {type: string, default: "09:30"}
        trading_end: {type: string, default: "16:00"}
        
        # Safety - Circuit Breakers
        circuit_breaker_daily_loss_pct: {type: number, default: 0.03}
        circuit_breaker_warning_drawdown_pct: {type: number, default: 0.10}
        circuit_breaker_max_drawdown_pct: {type: number, default: 0.15}
        circuit_breaker_consecutive_loss_limit: {type: integer, default: 5}
        circuit_breaker_auto_liquidate: {type: boolean, default: false}
        
        # Safety - Position Limits
        max_open_positions: {type: integer, default: 5}
        max_portfolio_heat_pct: {type: number, default: 0.10}
        no_new_trades_after: {type: string, default: "15:30"}
        
        # Safety - Liquidity
        min_avg_daily_volume: {type: integer, default: 1000000}
        min_price: {type: number, default: 5.00}
        max_spread_pct: {type: number, default: 0.002}
        min_market_cap: {type: integer, default: 1000000000}
        
        # Safety - Costs
        commission_per_share: {type: number, default: 0.005}
        min_commission: {type: number, default: 1.00}
        slippage_pct: {type: number, default: 0.001}
        spread_pct: {type: number, default: 0.0005}
        
        # Safety - Strategy
        strategy_min_win_rate: {type: number, default: 0.30}
        strategy_min_profit_factor: {type: number, default: 1.2}
        strategy_auto_disable: {type: boolean, default: true}
        
        # Safety - Sector
        max_sector_allocation_pct: {type: number, default: 0.30}
    
    # Backtest
    BacktestRequest:
      type: object
      properties:
        strategy: {type: string, example: "rsi_reversion"}
        symbol: {type: string, example: "AAPL"}
        days: {type: integer, example: 180}
        initial_capital: {type: number, example: 100000.00}
    
    BacktestResult:
      type: object
      properties:
        backtest_id: {type: string}
        strategy: {type: string}
        symbol: {type: string}
        total_return_pct: {type: number}
        max_drawdown_pct: {type: number}
        sharpe_ratio: {type: number}
        win_rate: {type: number}
        profit_factor: {type: number}
        total_trades: {type: integer}
        equity_curve: {type: array}

paths:
  
  # Health
  /health:
    get:
      summary: Health check
      responses:
        200:
          description: System healthy
          content:
            application/json:
              schema:
                type: object
                properties:
                  status: {type: string, example: "healthy"}
                  app: {type: string, example: "TradeMind AI"}
  
  # Portfolio
  /api/portfolio:
    get:
      summary: Get portfolio summary
      responses:
        200:
          content:
            application/json:
              schema: {$ref: '#/components/schemas/Portfolio'}
  
  /api/portfolio/holdings:
    get:
      summary: Get detailed holdings
      responses:
        200:
          content:
            application/json:
              schema:
                type: object
                properties:
                  holdings: {type: array, items: {$ref: '#/components/schemas/Holding'}}
                  total_holdings: {type: integer}
  
  # Trades
  /api/trades:
    get:
      summary: List trades
      parameters:
        - name: limit
          in: query
          schema: {type: integer, default: 20}
        - name: symbol
          in: query
          schema: {type: string}
      responses:
        200:
          content:
            application/json:
              schema:
                type: object
                properties:
                  trades: {type: array, items: {$ref: '#/components/schemas/Trade'}}
                  total: {type: integer}
  
  # Strategies
  /api/strategies:
    get:
      summary: List all strategies with performance
      responses:
        200:
          content:
            application/json:
              schema:
                type: object
                properties:
                  strategies: {type: array, items: {$ref: '#/components/schemas/Strategy'}}
  
  /api/strategies/{name}/toggle:
    post:
      summary: Enable/disable strategy
      parameters:
        - name: name
          in: path
          required: true
          schema: {type: string}
      responses:
        200:
          content:
            application/json:
              schema:
                type: object
                properties:
                  name: {type: string}
                  enabled: {type: boolean}
  
  /api/strategies/{name}/signal:
    get:
      summary: Get current signal for symbol
      parameters:
        - name: name
          in: path
          required: true
          schema: {type: string}
        - name: symbol
          in: query
          required: true
          schema: {type: string}
      responses:
        200:
          content:
            application/json:
              schema: {$ref: '#/components/schemas/Signal'}
  
  # Safety
  /api/safety/status:
    get:
      summary: Get complete safety status
      responses:
        200:
          content:
            application/json:
              schema: {$ref: '#/components/schemas/SafetyStatus'}
  
  /api/safety/circuit-breaker:
    get:
      summary: Get circuit breaker status
      responses:
        200:
          content:
            application/json:
              schema: {$ref: '#/components/schemas/CircuitBreakerStatus'}
  
  /api/safety/emergency-stop:
    post:
      summary: Emergency stop all trading
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                reason: {type: string}
      responses:
        200:
          content:
            application/json:
              schema:
                type: object
                properties:
                  status: {type: string, example: "halted"}
                  reason: {type: string}
  
  /api/safety/portfolio-heat:
    get:
      summary: Get portfolio heat details
      responses:
        200:
          content:
            application/json:
              schema: {$ref: '#/components/schemas/PortfolioHeat'}
  
  # Config
  /api/config:
    get:
      summary: Get all configuration
      responses:
        200:
          content:
            application/json:
              schema: {$ref: '#/components/schemas/Config'}
    
    post:
      summary: Update configuration
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                key: {type: string}
                value: {}
      responses:
        200:
          description: Config updated
  
  /api/config/{key}:
    get:
      summary: Get specific config value
      parameters:
        - name: key
          in: path
          required: true
          schema: {type: string}
      responses:
        200:
          content:
            application/json:
              schema:
                type: object
                properties:
                  key: {type: string}
                  value: {}
  
  # Backtest
  /api/backtest/run:
    post:
      summary: Run backtest
      requestBody:
        content:
          application/json:
            schema: {$ref: '#/components/schemas/BacktestRequest'}
      responses:
        200:
          content:
            application/json:
              schema: {$ref: '#/components/schemas/BacktestResult'}

# CLI Commands Reference
cli_commands:
  
  server:
    - trademind server start [--port 8000] [--reload]
    - trademind server stop
    - trademind server status
    - trademind server logs [--follow] [--lines 100]
    - trademind server restart
  
  portfolio:
    - trademind portfolio
    - trademind portfolio holdings
    - trademind portfolio performance [--days 30]
    - trademind portfolio sectors
  
  trades:
    - trademind trades list [--limit 20] [--symbol AAPL]
    - trademind trades today
    - trademind trades pnl [--symbol AAPL]
  
  strategies:
    - trademind strategies list
    - trademind strategies enable {name}
    - trademind strategies disable {name}
    - trademind strategies signal {name} --symbol AAPL
    - trademind strategies performance
    - trademind strategies backtest {name} --symbol AAPL --days 180
  
  safety:
    - trademind safety status
    - trademind safety circuit-breaker
    - trademind safety heat
    - trademind safety emergency-stop [--reason "..."]
    - trademind safety limits
  
  config:
    - trademind config show
    - trademind config get {key}
    - trademind config set {key} {value}
    - trademind config reset
    - trademind config validate
    - trademind safety daily-loss {pct}
    - trademind safety max-drawdown {pct}
    - trademind safety max-positions {count}
    - trademind safety check-interval {minutes}
  
  backtest:
    - trademind backtest run --strategy rsi --symbol AAPL --days 180
    - trademind backtest list [--limit 10]
    - trademind backtest results {id}
  
  data:
    - trademind data ingest --symbols AAPL,MSFT,TSLA
    - trademind data status
    - trademind data show {symbol} [--days 30]

# Configurable Variables
config_variables:
  
  trading:
    - starting_capital: {type: number, default: 100000, description: "Initial capital"}
    - max_position_pct: {type: number, default: 0.10, range: "0.01-0.50", description: "Max position as % of portfolio"}
    - check_interval_minutes: {type: integer, default: 15, range: "1-60", description: "Check frequency"}
    - trading_start: {type: string, default: "09:30", description: "Market open time"}
    - trading_end: {type: string, default: "16:00", description: "Market close time"}
  
  circuit_breakers:
    - circuit_breaker_daily_loss_pct: {type: number, default: 0.03, range: "0.01-0.10", description: "Halt trading at daily loss"}
    - circuit_breaker_warning_drawdown_pct: {type: number, default: 0.10, range: "0.05-0.20", description: "Warning at drawdown"}
    - circuit_breaker_max_drawdown_pct: {type: number, default: 0.15, range: "0.10-0.30", description: "Halt at max drawdown"}
    - circuit_breaker_consecutive_loss_limit: {type: integer, default: 5, range: "3-10", description: "Halt after N consecutive losses"}
    - circuit_breaker_auto_liquidate: {type: boolean, default: false, description: "Auto-close positions on halt"}
  
  position_limits:
    - max_open_positions: {type: integer, default: 5, range: "1-20", description: "Max concurrent positions"}
    - max_portfolio_heat_pct: {type: number, default: 0.10, range: "0.05-0.30", description: "Max capital at risk"}
    - no_new_trades_after: {type: string, default: "15:30", description: "Stop new trades after time"}
  
  liquidity:
    - min_avg_daily_volume: {type: integer, default: 1000000, description: "Min $ volume"}
    - min_price: {type: number, default: 5.00, description: "Min stock price"}
    - max_spread_pct: {type: number, default: 0.002, description: "Max bid-ask spread"}
    - min_market_cap: {type: integer, default: 1000000000, description: "Min market cap"}
  
  costs:
    - commission_per_share: {type: number, default: 0.005, description: "Commission per share"}
    - min_commission: {type: number, default: 1.00, description: "Minimum commission"}
    - slippage_pct: {type: number, default: 0.001, description: "Slippage estimate"}
    - spread_pct: {type: number, default: 0.0005, description: "Spread cost"}
  
  strategy:
    - strategy_min_win_rate: {type: number, default: 0.30, description: "Disable if below win rate"}
    - strategy_min_profit_factor: {type: number, default: 1.2, description: "Disable if below PF"}
    - strategy_auto_disable: {type: boolean, default: true, description: "Auto-disable bad strategies"}
  
  sector:
    - max_sector_allocation_pct: {type: number, default: 0.30, description: "Max per sector"}

# Safety Layer Hierarchy
safety_layers:
  layer_1_global:
    - Daily loss limit
    - Max drawdown (tiered: warning/halt)
    - Consecutive loss limit
    - Emergency kill switch
  
  layer_2_position:
    - Max position size
    - Stop loss / take profit
    - Time-based exit
    - Liquidity filters
  
  layer_3_portfolio:
    - Max open positions
    - Portfolio heat limit
    - Sector concentration
    - Correlation limits
  
  layer_4_strategy:
    - Win rate monitoring
    - Profit factor checks
    - Auto-disable underperforming
    - Performance attribution
  
  layer_5_execution:
    - Data validation
    - Order validation
    - Slippage monitoring
    - Audit logging

# Example Usage Flows
examples:
  
  daily_workflow:
    - trademind server start
    - trademind safety status
    - trademind portfolio
    - trademind strategies list
    - trademind trades today
  
  adjust_risk:
    - trademind config show
    - trademind safety max-positions 8
    - trademind safety daily-loss 2.5
    - trademind safety check-interval 10
    - trademind config validate
  
  emergency:
    - trademind safety status
    - trademind safety emergency-stop --reason "Market crash"
    - trademind safety circuit-breaker
    - trademind portfolio holdings
  
  backtest_strategy:
    - trademind strategies backtest rsi --symbol AAPL --days 180
    - trademind backtest list
    - trademind backtest results {id}
  
  add_symbols:
    - trademind data ingest --symbols NVDA,AMD,INTC
    - trademind data status
    - trademind config set watchlist ["AAPL","MSFT","NVDA","AMD","INTC"]
