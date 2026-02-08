# Safety Infrastructure Plan - TradeMind AI

## Overview

Focus on building robust risk management and safety controls for the existing swing trading system before adding new features. Based on OpenCode review: "front-load risk controls and validate early."

---

## Safety Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    SAFETY LAYERS                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Layer 1: GLOBAL CIRCUIT BREAKERS (Hard Stops)             │
│  ├── Daily loss limit: -3% of portfolio                    │
│  ├── Max drawdown: Halt at -15%, Warning at -10%           │
│  ├── Portfolio heat: Max 10% capital at risk               │
│  ├── Max open positions: 5 positions (prevent overexposure)│
│  ├── Consecutive loss limit: 5 losing trades               │
│  └── Emergency kill switch (manual + automatic)            │
│                                                             │
│  Layer 2: POSITION-LEVEL RISK (Per Trade)                  │
│  ├── Max position size: 10% of portfolio (fixed max)       │
│  ├── Volatility-based sizing (risk-based, not fixed 10%)   │
│  ├── Stop loss: -5% from entry                             │
│  ├── Take profit: +10% from entry                          │
│  ├── Time stop: Max 30 days holding                        │
│  └── Liquidity filters (min volume, price)                 │
│                                                             │
│  Layer 3: STRATEGY-LEVEL RISK (Per Strategy)               │
│  ├── Win rate monitoring (>30% over 20 trades)             │
│  ├── Profit factor check (>1.2)                            │
│  ├── Sector concentration limits (max 30% per sector)      │
│  └── Auto-disable underperforming strategies               │
│                                                             │
│  Layer 4: DATA & EXECUTION RISK                            │
│  ├── Data validation (stale data detection)                │
│  ├── Order validation (price, quantity checks)             │
│  └── Execution confirmation timeout                        │
│                                                             │
│  Layer 5: MONITORING & ALERTING                            │
│  ├── Real-time P&L monitoring                              │
│  ├── Alert on circuit breaker trigger                      │
│  ├── Daily risk report                                     │
│  └── Audit log of all decisions                            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Implementation Plan

### Phase 1: Global Circuit Breakers (Priority: CRITICAL)

**1.1 Daily Loss Limit**
```python
class CircuitBreaker:
    """Global trading halt mechanism"""
    
    DAILY_LOSS_LIMIT_PCT = 0.03  # 3%
    DRAWDOWN_WARNING_PCT = 0.10  # 10% - warning only
    DRAWDOWN_HALT_PCT = 0.15     # 15% - halt trading
    MAX_OPEN_POSITIONS = 5       # Prevent 10×10%=100% invested
    PORTFOLIO_HEAT_MAX_PCT = 0.10  # Max 10% capital at risk
    CONSECUTIVE_LOSS_LIMIT = 5
    
    def check_can_trade(self, portfolio: Portfolio) -> bool:
        # Check daily loss
        daily_pnl = portfolio.get_daily_pnl()
        if daily_pnl < -self.DAILY_LOSS_LIMIT_PCT * portfolio.total_value:
            self.trigger_circuit_breaker(
                reason=f"Daily loss limit hit: {daily_pnl:.2%}"
            )
            return False
        
        # Check drawdown (tiered approach)
        drawdown = portfolio.get_current_drawdown()
        if drawdown > self.DRAWDOWN_HALT_PCT:
            self.trigger_circuit_breaker(
                reason=f"Max drawdown exceeded: {drawdown:.2%}"
            )
            return False
        elif drawdown > self.DRAWDOWN_WARNING_PCT:
            logger.warning(f"Drawdown warning: {drawdown:.2%} (halt at {self.DRAWDOWN_HALT_PCT:.0%})")
            self.send_alert(
                level="WARNING",
                subject="Drawdown Warning",
                message=f"Portfolio drawdown at {drawdown:.2%}. Halt threshold: {self.DRAWDOWN_HALT_PCT:.0%}"
            )
        
        # Check max open positions
        open_positions = len([p for p in portfolio.positions if p.is_open])
        if open_positions >= self.MAX_OPEN_POSITIONS:
            logger.info(f"Max open positions reached: {open_positions}")
            return False  # Can't open new positions, but existing ones can continue
        
        # Check portfolio heat (total risk if all stops hit)
        portfolio_heat = self.calculate_portfolio_heat(portfolio)
        if portfolio_heat > self.PORTFOLIO_HEAT_MAX_PCT * portfolio.total_value:
            logger.warning(f"Portfolio heat {portfolio_heat:.2%} exceeds limit")
            return False  # Too much risk, can't add new positions
        
        # Check consecutive losses
        recent_trades = portfolio.get_recent_trades(n=10)
        consecutive_losses = self.count_consecutive_losses(recent_trades)
        if consecutive_losses >= self.CONSECUTIVE_LOSS_LIMIT:
            self.trigger_circuit_breaker(
                reason=f"{consecutive_losses} consecutive losses"
            )
            return False
        
        return True
    
    def calculate_portfolio_heat(self, portfolio: Portfolio) -> float:
        """
        Calculate total risk exposure if all stops are hit.
        Heat = sum of (position_value × stop_loss_pct) for all positions.
        """
        total_heat = 0.0
        for position in portfolio.positions:
            if position.is_open:
                position_value = position.shares * position.entry_price
                stop_risk = position_value * position.stop_loss_pct  # e.g., 5%
                total_heat += stop_risk
        return total_heat
    
    def trigger_circuit_breaker(self, reason: str):
        """Halt all trading and alert"""
        self.is_halted = True
        self.halt_reason = reason
        self.halt_time = datetime.now()
        
        # Log
        logger.critical(f"CIRCUIT BREAKER TRIGGERED: {reason}")
        
        # Alert
        self.send_alert(
            subject="🚨 TRADING HALTED",
            message=f"Circuit breaker triggered: {reason}"
        )
        
        # DO NOT auto-liquidate positions - manual review required
        logger.info("Trading halted - positions remain open for manual review")
```

**1.2 Emergency Kill Switch**
```python
# Web endpoint for emergency stop
@app.post("/api/emergency/stop")
async def emergency_stop(reason: str, user: CurrentUser):
    """Immediately halt all trading"""
    circuit_breaker.trigger_circuit_breaker(
        reason=f"MANUAL STOP by {user}: {reason}"
    )
    return {"status": "halted", "reason": reason}

# Physical file trigger (in case API is down)
def check_kill_switch_file():
    """Check for emergency stop file"""
    if Path("/tmp/trading_stop").exists():
        circuit_breaker.trigger_circuit_breaker(
            reason="Kill switch file detected"
        )
```

**1.3 Max Open Positions & Portfolio Heat Tracking**
```python
class PositionRiskManager:
    """
    Manage position count limits and portfolio heat (total risk at risk).
    Prevents scenario: 10 positions × 10% each = 100% capital deployed.
    """
    
    MAX_OPEN_POSITIONS = 5
    MAX_POSITION_PCT = 0.10  # 10% max per position (hard ceiling)
    PORTFOLIO_HEAT_MAX_PCT = 0.10  # 10% of capital at risk
    
    def can_open_position(self, portfolio: Portfolio, new_position_risk: float) -> Tuple[bool, str]:
        """
        Check if a new position can be opened.
        
        Args:
            portfolio: Current portfolio state
            new_position_risk: Dollar amount at risk (position_value × stop_loss_pct)
        
        Returns:
            (can_open, reason)
        """
        # Check position count
        open_count = len([p for p in portfolio.positions if p.is_open])
        if open_count >= self.MAX_OPEN_POSITIONS:
            return False, f"Max open positions ({self.MAX_OPEN_POSITIONS}) reached"
        
        # Check portfolio heat
        current_heat = self.calculate_portfolio_heat(portfolio)
        if current_heat + new_position_risk > self.PORTFOLIO_HEAT_MAX_PCT * portfolio.total_value:
            return False, f"Portfolio heat would exceed {self.PORTFOLIO_HEAT_MAX_PCT:.0%} limit"
        
        return True, "OK"
    
    def calculate_portfolio_heat(self, portfolio: Portfolio) -> float:
        """Calculate total risk if all stops hit."""
        heat = 0.0
        for position in portfolio.positions:
            if position.is_open and position.stop_loss_pct > 0:
                position_value = position.shares * position.entry_price
                heat += position_value * position.stop_loss_pct
        return heat
    
    def get_heat_status(self, portfolio: Portfolio) -> dict:
        """Get current heat status for monitoring."""
        heat = self.calculate_portfolio_heat(portfolio)
        heat_pct = heat / portfolio.total_value if portfolio.total_value > 0 else 0
        limit = self.PORTFOLIO_HEAT_MAX_PCT * portfolio.total_value
        
        return {
            'heat_dollars': heat,
            'heat_pct': heat_pct,
            'limit_dollars': limit,
            'limit_pct': self.PORTFOLIO_HEAT_MAX_PCT,
            'remaining': limit - heat,
            'status': 'danger' if heat_pct >= self.PORTFOLIO_HEAT_MAX_PCT else
                     'warning' if heat_pct >= self.PORTFOLIO_HEAT_MAX_PCT * 0.8 else
                     'ok'
        }
```

---

### Phase 2: Position-Level Risk Controls

**2.1 Volatility-Based Position Sizing**
```python
class VolatilityPositionSizer:
    """
    Size positions based on volatility (ATR) rather than fixed percentage.
    Goal: Equal risk per position, not equal capital per position.
    
    Formula: Position Size = Risk Amount / (ATR × multiplier)
    Example: $1,000 risk / ($2 ATR × 2) = 250 shares
    """
    
    RISK_PER_TRADE_PCT = 0.02  # 2% of portfolio per trade
    MAX_POSITION_PCT = 0.10    # 10% max (hard ceiling)
    ATR_PERIOD = 14
    ATR_MULTIPLIER = 2.0  # 2× ATR for stop distance
    
    def calculate_position_size(
        self, 
        portfolio: Portfolio, 
        symbol: str, 
        entry_price: float
    ) -> dict:
        """
        Calculate position size based on volatility (ATR).
        
        Returns dict with:
        - shares: Number of shares to buy
        - position_value: Dollar value of position
        - position_pct: % of portfolio
        - stop_price: Stop loss price level
        - risk_amount: Dollar amount at risk
        - risk_pct: % of portfolio at risk
        """
        # Get ATR (Average True Range)
        atr = self.get_atr(symbol, period=self.ATR_PERIOD)
        if atr is None or atr <= 0:
            logger.warning(f"Could not calculate ATR for {symbol}, using fixed sizing")
            return self._fallback_sizing(portfolio, entry_price)
        
        # Calculate stop distance in dollars (2× ATR)
        stop_distance = atr * self.ATR_MULTIPLIER
        
        # Calculate risk amount (2% of portfolio)
        risk_amount = portfolio.total_value * self.RISK_PER_TRADE_PCT
        
        # Calculate position size: Risk Amount / Stop Distance
        shares = int(risk_amount / stop_distance)
        
        # Calculate position value
        position_value = shares * entry_price
        position_pct = position_value / portfolio.total_value
        
        # Enforce max position size (10% ceiling)
        max_position_value = portfolio.total_value * self.MAX_POSITION_PCT
        if position_value > max_position_value:
            shares = int(max_position_value / entry_price)
            position_value = shares * entry_price
            position_pct = self.MAX_POSITION_PCT
            risk_amount = shares * stop_distance
            logger.info(f"Position capped at {self.MAX_POSITION_PCT:.0%} max: {shares} shares")
        
        # Calculate stop price
        stop_price = entry_price - stop_distance
        
        return {
            'shares': shares,
            'position_value': position_value,
            'position_pct': position_pct,
            'stop_price': stop_price,
            'stop_distance': stop_distance,
            'stop_distance_pct': stop_distance / entry_price,
            'risk_amount': risk_amount,
            'risk_pct': risk_amount / portfolio.total_value,
            'atr': atr,
            'method': 'volatility'
        }
    
    def _fallback_sizing(self, portfolio: Portfolio, entry_price: float) -> dict:
        """Fallback to fixed 10% sizing if ATR unavailable."""
        position_value = portfolio.total_value * 0.10
        shares = int(position_value / entry_price)
        
        return {
            'shares': shares,
            'position_value': shares * entry_price,
            'position_pct': 0.10,
            'stop_price': entry_price * 0.95,  # Fixed 5% stop
            'stop_distance_pct': 0.05,
            'risk_amount': shares * entry_price * 0.05,
            'risk_pct': 0.005,  # 0.5%
            'atr': None,
            'method': 'fallback_fixed'
        }
    
    def get_atr(self, symbol: str, period: int = 14) -> Optional[float]:
        """Calculate Average True Range for volatility measurement."""
        try:
            hist = yf.Ticker(symbol).history(period=f"{period + 10}d")
            if len(hist) < period:
                return None
            
            # Calculate True Range
            high_low = hist['High'] - hist['Low']
            high_close = abs(hist['High'] - hist['Close'].shift())
            low_close = abs(hist['Low'] - hist['Close'].shift())
            
            true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            atr = true_range.rolling(window=period).mean().iloc[-1]
            
            return float(atr) if not pd.isna(atr) else None
        except Exception as e:
            logger.warning(f"Error calculating ATR for {symbol}: {e}")
            return None
```

**2.2 Liquidity Filters**
```python
class LiquidityFilter:
    """Ensure we only trade liquid stocks"""
    
    MIN_AVG_DAILY_VOLUME = 1_000_000  # $1M
    MIN_PRICE = 5.00
    MAX_SPREAD_PCT = 0.002  # 0.2%
    MIN_MARKET_CAP = 1_000_000_000  # $1B
    
    def validate(self, symbol: str) -> Tuple[bool, str]:
        # Get fundamentals
        info = yf.Ticker(symbol).info
        
        # Check price
        if info.get('currentPrice', 0) < self.MIN_PRICE:
            return False, f"Price {info['currentPrice']} below ${self.MIN_PRICE}"
        
        # Check volume
        avg_volume = info.get('averageVolume', 0)
        avg_price = info.get('currentPrice', 0)
        dollar_volume = avg_volume * avg_price
        if dollar_volume < self.MIN_AVG_DAILY_VOLUME:
            return False, f"Volume ${dollar_volume:,.0f} below ${self.MIN_AVG_DAILY_VOLUME:,.0f}"
        
        # Check market cap
        market_cap = info.get('marketCap', 0)
        if market_cap < self.MIN_MARKET_CAP:
            return False, f"Market cap ${market_cap:,.0f} below ${self.MIN_MARKET_CAP:,.0f}"
        
        # Check spread (if available)
        bid = info.get('bid', 0)
        ask = info.get('ask', 0)
        if bid > 0 and ask > 0:
            spread_pct = (ask - bid) / ((ask + bid) / 2)
            if spread_pct > self.MAX_SPREAD_PCT:
                return False, f"Spread {spread_pct:.2%} above {self.MAX_SPREAD_PCT:.2%}"
        
        return True, "OK"
```

**2.3 Earnings & News Filters**
```python
class EarningsFilter:
    """Avoid trading around earnings (1 day before only)"""
    
    AVOID_DAYS_BEFORE = 1  # Reduced from 2 days per review
    AVOID_DAYS_AFTER = 1
    
    def is_safe_to_trade(self, symbol: str) -> bool:
        """Check if symbol has earnings soon"""
        try:
            calendar = yf.Ticker(symbol).calendar
            if calendar is None or calendar.empty:
                return True
            
            next_earnings = calendar.index[0]
            days_to_earnings = (next_earnings - datetime.now()).days
            
            if -self.AVOID_DAYS_AFTER <= days_to_earnings <= self.AVOID_DAYS_BEFORE:
                logger.warning(f"{symbol}: Earnings in {days_to_earnings} days, skipping")
                return False
            
            return True
        except:
            return True  # If can't get data, allow trade
```

**2.4 Time-Based Restrictions**
```python
class TimeFilter:
    """Market hours and time-based rules"""
    
    MARKET_OPEN = time(9, 30, tzinfo=ZoneInfo("America/New_York"))
    MARKET_CLOSE = time(16, 0, tzinfo=ZoneInfo("America/New_York"))
    NO_NEW_TRADES_AFTER = time(15, 30, tzinfo=ZoneInfo("America/New_York"))
    
    def can_trade_now(self) -> bool:
        now = datetime.now(ZoneInfo("America/New_York"))
        
        # Check market hours
        if not self.is_market_open():
            return False
        
        # Check for holidays
        if self.is_market_holiday(now.date()):
            return False
        
        return True
    
    def is_market_open(self) -> bool:
        now = datetime.now(ZoneInfo("America/New_York"))
        current_time = now.time()
        
        # Check if weekday
        if now.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return False
        
        return self.MARKET_OPEN <= current_time <= self.MARKET_CLOSE
```

---

### Phase 3: Strategy-Level Risk

**3.1 Strategy Performance Monitoring**
```python
class StrategyMonitor:
    """Auto-disable underperforming strategies"""
    
    MIN_WIN_RATE = 0.30  # 30%
    MIN_PROFIT_FACTOR = 1.2
    MIN_TRADES_FOR_EVAL = 20
    
    def evaluate_strategy(self, strategy_name: str) -> bool:
        """Returns True if strategy should continue running"""
        trades = self.get_strategy_trades(strategy_name, n=self.MIN_TRADES_FOR_EVAL)
        
        if len(trades) < self.MIN_TRADES_FOR_EVAL:
            return True  # Not enough data
        
        # Calculate metrics
        wins = [t for t in trades if t.pnl > 0]
        losses = [t for t in trades if t.pnl <= 0]
        
        win_rate = len(wins) / len(trades)
        
        gross_profit = sum(t.pnl for t in wins)
        gross_loss = abs(sum(t.pnl for t in losses))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Check thresholds
        if win_rate < self.MIN_WIN_RATE:
            logger.warning(f"{strategy_name}: Win rate {win_rate:.1%} below {self.MIN_WIN_RATE:.1%}")
            return False
        
        if profit_factor < self.MIN_PROFIT_FACTOR:
            logger.warning(f"{strategy_name}: Profit factor {profit_factor:.2f} below {self.MIN_PROFIT_FACTOR}")
            return False
        
        return True
```

**3.2 Sector Concentration Limits (Replaces Correlation Monitoring)**
```python
class SectorConcentrationMonitor:
    """
    Simpler alternative to correlation monitoring.
    Prevents over-concentration by sector (e.g., all tech stocks).
    """
    
    MAX_SECTOR_PCT = 0.30  # Max 30% of portfolio in any one sector
    
    # Sector mapping (simplified - can be expanded)
    SECTOR_ETF_MAP = {
        'XLK': 'Technology',
        'XLF': 'Financials',
        'XLE': 'Energy',
        'XLI': 'Industrials',
        'XLP': 'Consumer Staples',
        'XLY': 'Consumer Discretionary',
        'XLB': 'Materials',
        'XLU': 'Utilities',
        'XLV': 'Healthcare',
        'XLRE': 'Real Estate',
        'XLC': 'Communication Services'
    }
    
    def __init__(self):
        self.symbol_to_sector = {}
    
    def can_add_to_sector(self, portfolio: Portfolio, symbol: str) -> Tuple[bool, str]:
        """
        Check if adding this symbol would exceed sector limits.
        """
        sector = self.get_sector(symbol)
        if not sector:
            return True, "Unknown sector - allowing trade"
        
        # Calculate current sector allocation
        sector_value = 0.0
        for position in portfolio.positions:
            if position.is_open:
                pos_sector = self.get_sector(position.symbol)
                if pos_sector == sector:
                    sector_value += position.shares * position.current_price
        
        # Add proposed position (estimate)
        proposed_value = self.estimate_position_value(portfolio, symbol)
        new_sector_value = sector_value + proposed_value
        new_sector_pct = new_sector_value / portfolio.total_value
        
        if new_sector_pct > self.MAX_SECTOR_PCT:
            return False, f"{sector} allocation would be {new_sector_pct:.1%} (max {self.MAX_SECTOR_PCT:.0%})"
        
        return True, f"{sector} at {new_sector_pct:.1%}"
    
    def get_sector(self, symbol: str) -> Optional[str]:
        """Get sector for a symbol (with caching)."""
        if symbol in self.symbol_to_sector:
            return self.symbol_to_sector[symbol]
        
        try:
            # Fetch from yfinance
            info = yf.Ticker(symbol).info
            sector = info.get('sector')
            if sector:
                self.symbol_to_sector[symbol] = sector
                return sector
            
            # Fallback to industry
            industry = info.get('industry')
            if industry:
                self.symbol_to_sector[symbol] = industry
                return industry
            
            return None
        except Exception as e:
            logger.warning(f"Could not get sector for {symbol}: {e}")
            return None
    
    def estimate_position_value(self, portfolio: Portfolio, symbol: str) -> float:
        """Estimate position value for proposed trade."""
        # Use volatility-based sizer estimate (roughly 2-5% of portfolio)
        return portfolio.total_value * 0.05
    
    def get_sector_allocation(self, portfolio: Portfolio) -> Dict[str, float]:
        """Get current sector allocation breakdown."""
        allocations = {}
        
        for position in portfolio.positions:
            if position.is_open:
                sector = self.get_sector(position.symbol) or 'Unknown'
                value = position.shares * position.current_price
                allocations[sector] = allocations.get(sector, 0) + value
        
        # Convert to percentages
        for sector in allocations:
            allocations[sector] = allocations[sector] / portfolio.total_value
        
        return allocations
```

---

### Phase 4: Transaction Cost Modeling

**4.1 Realistic Cost Model**
```python
class TransactionCostModel:
    """Model all trading costs for realistic backtesting"""
    
    COMMISSION_PER_SHARE = 0.005  # $0.005 per share (e.g., IBKR)
    MIN_COMMISSION = 1.00  # $1 minimum
    MAX_COMMISSION_PCT = 0.01  # 1% cap
    
    SLIPPAGE_PCT = 0.001  # 0.1% slippage
    SPREAD_PCT = 0.0005   # 0.05% spread (average)
    
    def calculate_cost(self, quantity: int, price: float, is_market_order: bool = True) -> float:
        """Calculate total transaction cost"""
        notional = quantity * price
        
        # Commission
        commission = max(
            quantity * self.COMMISSION_PER_SHARE,
            self.MIN_COMMISSION
        )
        commission = min(commission, notional * self.MAX_COMMISSION_PCT)
        
        # Slippage (market orders only)
        slippage = notional * self.SLIPPAGE_PCT if is_market_order else 0
        
        # Spread (half spread on entry, half on exit)
        spread_cost = notional * self.SPREAD_PCT
        
        total_cost = commission + slippage + spread_cost
        
        return {
            'commission': commission,
            'slippage': slippage,
            'spread': spread_cost,
            'total': total_cost,
            'total_pct': total_cost / notional
        }
```

---

### Phase 5: Data Validation

**5.1 Data Quality Checks**
```python
class DataValidator:
    """Validate market data before using"""
    
    MAX_DATA_AGE_MINUTES = 15
    MAX_PRICE_CHANGE_PCT = 0.20  # 20% (halt/suspicion check)
    
    def validate_price_data(self, symbol: str, current_price: float, 
                           previous_price: float, timestamp: datetime) -> Tuple[bool, str]:
        """Check if price data is valid"""
        
        # Check staleness
        age = (datetime.now() - timestamp).total_seconds() / 60
        if age > self.MAX_DATA_AGE_MINUTES:
            return False, f"Data stale: {age:.1f} min old"
        
        # Check for suspicious price moves
        if previous_price > 0:
            change_pct = abs(current_price - previous_price) / previous_price
            if change_pct > self.MAX_PRICE_CHANGE_PCT:
                return False, f"Suspicious move: {change_pct:.1%}"
        
        # Check for zero/null prices
        if current_price <= 0 or pd.isna(current_price):
            return False, "Invalid price (zero/null)"
        
        return True, "OK"
```

---

### Phase 6: Alerting & Monitoring

**6.1 Real-Time Alerts**
```python
class AlertManager:
    """Send alerts for critical events"""
    
    def send_alert(self, level: str, subject: str, message: str):
        """Send alert via multiple channels"""
        
        # Log
        if level == "CRITICAL":
            logger.critical(f"ALERT: {subject} - {message}")
        elif level == "WARNING":
            logger.warning(f"ALERT: {subject} - {message}")
        
        # Email
        if level in ["CRITICAL", "ERROR"]:
            self.send_email(subject, message)
        
        # SMS (for critical only)
        if level == "CRITICAL":
            self.send_sms(f"CRITICAL: {subject}")
    
    def check_and_alert(self, portfolio: Portfolio):
        """Periodic check for alerts"""
        # Daily loss approaching limit
        daily_pnl = portfolio.get_daily_pnl()
        daily_pnl_pct = daily_pnl / portfolio.total_value
        
        if daily_pnl_pct < -0.02:  # 2% loss
            self.send_alert(
                "WARNING",
                "Daily Loss Alert",
                f"Daily loss at {daily_pnl_pct:.2%}. Circuit breaker at -3%."
            )
```

---

## Database Schema Updates

```sql
-- Circuit breaker log
CREATE TABLE circuit_breaker_events (
    id SERIAL PRIMARY KEY,
    triggered_at TIMESTAMPTZ DEFAULT NOW(),
    reason TEXT NOT NULL,
    portfolio_value DECIMAL(15, 2),
    daily_pnl DECIMAL(15, 2),
    drawdown DECIMAL(8, 4),
    portfolio_heat_pct DECIMAL(5, 4),  -- Total risk exposure
    reset_at TIMESTAMPTZ,
    reset_by TEXT
);

-- Risk events log
CREATE TABLE risk_events (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    event_type TEXT NOT NULL,  -- 'position_rejected', 'strategy_disabled', etc.
    symbol TEXT,
    strategy TEXT,
    reason TEXT,
    details JSONB
);

-- Portfolio heat tracking
CREATE TABLE portfolio_heat_snapshots (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    total_value DECIMAL(15, 2),
    heat_amount DECIMAL(15, 2),
    heat_pct DECIMAL(5, 4),
    open_positions INTEGER,
    max_positions INTEGER
);

-- Add to existing trades table
ALTER TABLE trades ADD COLUMN 
    transaction_costs DECIMAL(10, 4) DEFAULT 0;

ALTER TABLE trades ADD COLUMN 
    slippage DECIMAL(10, 4) DEFAULT 0;

ALTER TABLE trades ADD COLUMN
    atr_at_entry DECIMAL(10, 4);  -- ATR for volatility sizing

ALTER TABLE trades ADD COLUMN
    position_heat DECIMAL(10, 4);  -- Risk amount for this position

-- Strategy performance tracking
CREATE TABLE strategy_performance (
    strategy_name TEXT PRIMARY KEY,
    total_trades INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    losing_trades INTEGER DEFAULT 0,
    gross_profit DECIMAL(15, 2) DEFAULT 0,
    gross_loss DECIMAL(15, 2) DEFAULT 0,
    win_rate DECIMAL(5, 4) GENERATED ALWAYS AS (
        CASE WHEN total_trades > 0 
        THEN winning_trades::decimal / total_trades 
        ELSE 0 END
    ) STORED,
    profit_factor DECIMAL(8, 4) GENERATED ALWAYS AS (
        CASE WHEN gross_loss > 0 
        THEN gross_profit / ABS(gross_loss) 
        ELSE NULL END
    ) STORED,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Sector concentration tracking
CREATE TABLE sector_allocations (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    sector TEXT NOT NULL,
    allocation_pct DECIMAL(5, 4),
    value DECIMAL(15, 2)
);
```

---

## Implementation Order

### Week 1: Critical Safety (Days 1-3)
1. ✅ Circuit breaker with daily loss limit
2. ✅ Emergency kill switch (API + file)
3. ✅ Time-based restrictions (market hours)
4. ✅ **MAX OPEN POSITIONS** (limit to 5 positions)

### Week 2: Position Risk & Costs (Days 4-6)
1. ✅ Liquidity filters (volume, price, spread)
2. ✅ Transaction cost modeling
3. ✅ **PORTFOLIO HEAT TRACKING** (10% max capital at risk)
4. ✅ **VOLATILITY-BASED POSITION SIZING** (ATR-based)

### Week 3: Data, Alerts & Strategy (Days 7-9)
1. ✅ Data validation layer
2. ✅ Earnings/news filters (1 day before)
3. ✅ Alert system (email/SMS)
4. ✅ Strategy performance monitoring
5. ✅ Sector concentration limits (replaces correlation)

### Week 4: Testing & Hardening (Days 10-12)
1. Stress test circuit breakers
2. Simulate data provider failures
3. Backtest with transaction costs
4. Test portfolio heat scenarios
5. Document all safety procedures

---

## Deferred to Later (Post-MVP)

The following items are intentionally deferred to keep the initial implementation focused:

1. **Multi-provider fallback** - Yahoo daily data is reliable enough for swing trading; single provider sufficient for MVP
2. **Complex correlation monitoring matrix** - Replaced with simpler sector concentration limits for MVP

These can be revisited after core safety infrastructure is proven stable.

---

## Testing Strategy

```python
# Test circuit breaker
def test_daily_loss_limit():
    portfolio = create_portfolio(value=100000)
    portfolio.daily_pnl = -3500  # -3.5%
    
    cb = CircuitBreaker()
    can_trade = cb.check_can_trade(portfolio)
    
    assert not can_trade
    assert cb.is_halted
    assert "Daily loss limit" in cb.halt_reason

# Test tiered drawdown
def test_drawdown_warning():
    portfolio = create_portfolio(value=100000, peak_value=111111)  # -10% drawdown
    
    cb = CircuitBreaker()
    can_trade = cb.check_can_trade(portfolio)
    
    assert can_trade  # Should still be able to trade at -10%
    # Warning should be logged/sent

# Test max positions limit
def test_max_positions():
    portfolio = create_portfolio(value=100000)
    portfolio.positions = [create_position() for _ in range(5)]  # 5 open positions
    
    prm = PositionRiskManager()
    can_open, reason = prm.can_open_position(portfolio, 1000)
    
    assert not can_open
    assert "Max open positions" in reason

# Test portfolio heat
def test_portfolio_heat():
    portfolio = create_portfolio(value=100000)
    # Add positions that would exceed heat limit
    portfolio.positions = [
        create_position(risk_amount=3000),  # 3%
        create_position(risk_amount=3000),  # 3%
        create_position(risk_amount=3000),  # 3%
        create_position(risk_amount=3000),  # 3% - total 12%, exceeds 10% limit
    ]
    
    prm = PositionRiskManager()
    heat_status = prm.get_heat_status(portfolio)
    
    assert heat_status['status'] == 'danger'

# Test volatility sizing
def test_volatility_position_sizing():
    sizer = VolatilityPositionSizer()
    portfolio = create_portfolio(value=100000)
    
    # Mock ATR of $2 for a $100 stock
    with mock_atr(symbol="AAPL", atr=2.0, price=100.0):
        result = sizer.calculate_position_size(portfolio, "AAPL", 100.0)
        
        # Risk = 2% of portfolio = $2,000
        # Stop distance = 2 × ATR = $4
        # Shares = $2,000 / $4 = 500 shares
        assert result['shares'] == 500
        assert result['method'] == 'volatility'

# Test liquidity filter
def test_low_volume_rejection():
    lf = LiquidityFilter()
    
    # Mock low-volume stock
    with mock_yf_ticker(volume=1000, price=50):
        ok, reason = lf.validate("LOWVOL")
        assert not ok
        assert "Volume" in reason

# Test sector concentration
def test_sector_concentration():
    scm = SectorConcentrationMonitor()
    portfolio = create_portfolio(value=100000)
    
    # Add 3 tech positions at 10% each = 30%
    portfolio.positions = [
        create_position(symbol="AAPL", sector="Technology", value=10000),
        create_position(symbol="MSFT", sector="Technology", value=10000),
        create_position(symbol="GOOGL", sector="Technology", value=10000),
    ]
    
    can_add, reason = scm.can_add_to_sector(portfolio, "NVDA")  # Also tech
    
    assert not can_add
    assert "Technology" in reason

# Test transaction costs
def test_cost_model():
    cm = TransactionCostModel()
    costs = cm.calculate_cost(quantity=100, price=150.00)
    
    assert costs['commission'] == 1.00  # Min commission
    assert costs['total_pct'] > 0.001  # At least 0.1%
```

---

## Configuration

```yaml
# safety.yaml
safety:
  circuit_breakers:
    daily_loss_limit_pct: 0.03
    drawdown_warning_pct: 0.10  # Tiered: warning at 10%
    drawdown_halt_pct: 0.15     # Tiered: halt at 15%
    consecutive_loss_limit: 5
    auto_close_on_halt: false   # DO NOT liquidate - manual review only
  
  position_risk:
    max_open_positions: 5       # Prevent 10×10%=100% invested
    max_position_pct: 0.10      # 10% max per position (hard ceiling)
    volatility_risk_per_trade_pct: 0.02  # 2% of portfolio at risk
    atr_period: 14
    atr_multiplier: 2.0         # 2× ATR for stop distance
    portfolio_heat_max_pct: 0.10  # Max 10% capital at risk
    stop_loss_pct: 0.05
    take_profit_pct: 0.10
    max_hold_days: 30
  
  liquidity:
    min_avg_daily_volume: 1000000
    min_price: 5.00
    max_spread_pct: 0.002
    min_market_cap: 1000000000
  
  time:
    market_hours_only: true
    no_new_trades_after: "15:30"
    avoid_earnings_days_before: 1  # Reduced from 2 days
    avoid_earnings_days_after: 1
  
  strategy:
    min_win_rate: 0.30
    min_profit_factor: 1.2
    min_trades_for_eval: 20
    auto_disable_underperforming: true
    max_sector_pct: 0.30        # 30% max per sector (replaces correlation)
  
  costs:
    commission_per_share: 0.005
    min_commission: 1.00
    max_commission_pct: 0.01
    slippage_pct: 0.001
    spread_pct: 0.0005
  
  alerts:
    email_on_critical: true
    sms_on_critical: true
    daily_report_time: "17:00"
```

---

## Success Criteria

✅ **Phase 1 Complete When:**
- Circuit breaker triggers correctly on -3% daily loss
- Kill switch works from API and file
- Trading stops outside market hours
- **Max open positions enforced (5 positions)**

✅ **Phase 2 Complete When:**
- Low-volume stocks are rejected
- Transaction costs reduce backtest returns by realistic amount
- **Portfolio heat tracked and enforced (max 10% risk)**
- **Volatility-based sizing working (ATR-based)**

✅ **Phase 3 Complete When:**
- Data validation catches stale/suspicious data
- Alerts sent for all critical events
- Strategy auto-disables after 20 losing trades
- Sector concentration limits enforced (30% per sector)
- All decisions logged with audit trail

---

## Summary

This plan prioritizes **capital preservation over profit generation**. The safety infrastructure will:

1. **Prevent catastrophic losses** via circuit breakers (tiered drawdown warning/halt)
2. **Prevent over-concentration** via max open positions (5) and sector limits (30%)
3. **Control risk exposure** via portfolio heat tracking (10% max at risk)
4. **Optimize position sizing** via volatility-based sizing (ATR method)
5. **Ensure realistic backtesting** via transaction costs
6. **Avoid bad trades** via liquidity/earnings filters (1 day before)
7. **Auto-disable bad strategies** via performance monitoring
8. **Alert on problems** via multi-channel notifications

**Key Changes from Original Plan:**
- Added max open positions limit (5 positions)
- Added portfolio heat tracking (10% capital at risk)
- Added volatility-based position sizing (replaces fixed 10%)
- Changed drawdown to tiered: warning at 10%, halt at 15%
- Replaced complex correlation monitoring with simpler sector concentration limits (30% per sector)
- Reduced earnings filter from 2 days to 1 day before
- **Auto-liquidate on halt: FALSE** (manual review required - safer)
- Deferred multi-provider fallback and complex correlation matrix to post-MVP

**Estimated Timeline:** 2-3 weeks for full safety infrastructure.
