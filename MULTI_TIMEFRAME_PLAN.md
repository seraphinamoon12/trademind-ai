# Multi-Timeframe Trading Plan

## Overview

Add day trading capabilities to the existing TradeMind AI while maintaining swing trading. Support both timeframes simultaneously with different strategies.

---

## Architecture Changes

### 1. Dual Timeframe Support

```
┌─────────────────────────────────────────────────────────────┐
│                    TRADEMIND AI                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────┐  ┌─────────────────────┐          │
│  │  SWING TRADING      │  │  DAY TRADING        │          │
│  │  (Daily timeframe)  │  │  (5min timeframe)   │          │
│  │                     │  │                     │          │
│  │  • Daily RSI        │  │  • RSI-14 (5min)    │          │
│  │  • MA 50/200        │  │  • EMA 9/21         │          │
│  │  • Trend following  │  │  • VWAP             │          │
│  │  • Hold: days       │  │  • Hold: hours      │          │
│  │                     │  │  • Volume analysis  │          │
│  └─────────────────────┘  └─────────────────────┘          │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │         PORTFOLIO MANAGER (Unified)                 │   │
│  │  - Separate position tracking per timeframe         │   │
│  │  - Shared capital pool with allocation limits       │   │
│  │  - Combined P&L reporting                           │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Data Infrastructure Changes

### Database Schema Updates

```sql
-- Separate hypertables for different timeframes
CREATE TABLE market_data_daily (...);  -- Existing
CREATE TABLE market_data_5min (...);   -- New

-- Track which timeframe generated the signal
ALTER TABLE trades ADD COLUMN timeframe TEXT;  -- 'daily', '5min'
ALTER TABLE trades ADD COLUMN strategy_type TEXT;  -- 'swing', 'day'

-- Separate holdings per timeframe
CREATE TABLE holdings_swing (...);
CREATE TABLE holdings_day (...);
```

### Data Ingestion

```python
class MultiTimeframeIngestion:
    """Ingest data for multiple timeframes"""
    
    def ingest_daily(self, symbol):
        # Existing: daily candles
        return yf.download(symbol, interval="1d")
    
    def ingest_intraday(self, symbol, interval="5m"):
        # New: intraday candles
        # Note: yfinance limits: 1m=7days, 5m=60days
        return yf.download(symbol, interval=interval, period="60d")
```

---

## Strategy Configurations

### Swing Trading (Existing)
```yaml
swing_trading:
  enabled: true
  interval: "1d"
  check_frequency_minutes: 15
  
  strategies:
    rsi_mean_reversion:
      period: 14  # 14 days
      oversold: 30
      overbought: 70
    
    ma_crossover:
      fast: 50    # 50 days
      slow: 200   # 200 days
  
  risk:
    max_position_pct: 0.10
    stop_loss_pct: 0.05
    take_profit_pct: 0.10
    max_hold_days: 30
```

### Day Trading (New)
```yaml
day_trading:
  enabled: true
  interval: "5m"
  check_frequency_minutes: 1
  
  strategies:
    rsi_scalping:
      period: 14  # 14 five-minute periods = 70 minutes
      oversold: 25
      overbought: 75
    
    ema_crossover:
      fast: 9     # 9 periods (45 min)
      slow: 21    # 21 periods (105 min)
    
    vwap_bounce:
      lookback: 50  # periods
      deviation_threshold: 0.002  # 0.2%
  
  risk:
    max_position_pct: 0.05        # Smaller positions
    stop_loss_pct: 0.015          # Tighter stops (1.5%)
    take_profit_pct: 0.03         # Quick profits (3%)
    max_hold_minutes: 240         # Exit by end of day
    max_trades_per_day: 10        # Limit overtrading
    daily_loss_limit_pct: 0.02    # Stop after 2% loss
```

---

## New Day Trading Strategies

### 1. RSI Scalping
```python
class RSIScalpingStrategy:
    """Quick mean reversion on 5m timeframe"""
    
    def generate_signal(self, df):
        rsi = calculate_rsi(df['close'], period=14)
        
        if rsi < 25:  # More extreme than swing
            return Signal.BUY, confidence=0.7
        elif rsi > 75:
            return Signal.SELL, confidence=0.7
        
        return Signal.HOLD
```

### 2. EMA Crossover (Intraday)
```python
class EMACrossoverStrategy:
    """9/21 EMA crossover for day trading"""
    
    def generate_signal(self, df):
        df['ema_9'] = df['close'].ewm(span=9).mean()
        df['ema_21'] = df['close'].ewm(span=21).mean()
        
        if crossover(df['ema_9'], df['ema_21']):
            return Signal.BUY
        elif crossover(df['ema_21'], df['ema_9']):
            return Signal.SELL
        
        return Signal.HOLD
```

### 3. VWAP Bounce
```python
class VWAPBounceStrategy:
    """Trade bounces off VWAP"""
    
    def generate_signal(self, df):
        vwap = calculate_vwap(df)
        price = df['close'].iloc[-1]
        deviation = (price - vwap) / vwap
        
        if deviation < -0.002:  # Price below VWAP by 0.2%
            return Signal.BUY  # Expect bounce back to VWAP
        elif deviation > 0.002:
            return Signal.SELL
        
        return Signal.HOLD
```

---

## Portfolio Management Changes

### Capital Allocation

```python
class MultiTimeframePortfolio:
    """Manage capital across timeframes"""
    
    def __init__(self, total_capital):
        self.total_capital = total_capital
        
        # Allocation split
        self.swing_allocation = 0.60  # 60% to swing
        self.day_allocation = 0.40    # 40% to day
        
        self.swing_portfolio = Portfolio(
            capital=total_capital * self.swing_allocation
        )
        self.day_portfolio = Portfolio(
            capital=total_capital * self.day_allocation
        )
    
    def get_available_capital(self, timeframe):
        if timeframe == 'swing':
            return self.swing_portfolio.cash
        else:
            return self.day_portfolio.cash
```

### Position Tracking

```python
class PositionManager:
    """Track positions separately per timeframe"""
    
    def __init__(self):
        self.swing_positions = {}  # symbol -> Position
        self.day_positions = {}    # symbol -> Position
    
    def add_position(self, symbol, quantity, price, timeframe):
        position = Position(
            symbol=symbol,
            quantity=quantity,
            entry_price=price,
            timeframe=timeframe,
            entry_time=now()
        )
        
        if timeframe == 'swing':
            self.swing_positions[symbol] = position
        else:
            self.day_positions[symbol] = position
    
    def close_day_positions(self):
        """Close all day trades at market close"""
        for symbol, position in self.day_positions.items():
            if not position.is_closed:
                self.market_sell(symbol, position.quantity)
```

---

## Risk Management Per Timeframe

### Swing Risk Rules
- Max position: 10% of portfolio
- Stop loss: 5%
- Take profit: 10%
- Max hold: 30 days

### Day Trading Risk Rules
- Max position: 5% of portfolio (smaller)
- Stop loss: 1.5% (tighter)
- Take profit: 3% (quick)
- Max hold: 4 hours (exit EOD)
- Max trades/day: 10 (prevent overtrading)
- Daily loss limit: 2% (stop trading if down)
- Time restriction: No new trades after 3:30 PM

---

## Execution Engine Changes

### Dual Check Loop

```python
class MultiTimeframeExecutor:
    """Run both swing and day trading checks"""
    
    def __init__(self):
        self.swing_checker = TradingChecker(
            timeframe='1d',
            interval_minutes=15
        )
        self.day_checker = TradingChecker(
            timeframe='5m',
            interval_minutes=1
        )
    
    async def run(self):
        while True:
            # Check swing trades (every 15 min)
            if self.should_check_swing():
                await self.swing_checker.check_signals()
            
            # Check day trades (every 1 min)
            if self.should_check_day():
                await self.day_checker.check_signals()
            
            # Close day positions at 3:45 PM
            if self.is_market_close_time():
                await self.close_all_day_positions()
            
            await asyncio.sleep(60)  # 1 minute loop
```

---

## Dashboard Updates

### Separate Views

```
Dashboard Structure:
├── Overview (Combined P&L)
│   ├── Total Portfolio Value
│   ├── Swing Trading P&L
│   ├── Day Trading P&L
│   └── Capital Allocation
│
├── Swing Trading Tab
│   ├── Daily Chart
│   ├── Swing Positions
│   ├── Daily Signals
│   └── Swing Performance
│
├── Day Trading Tab
│   ├── 5m Chart
│   ├── Active Day Positions
│   ├── Today's Trades
│   ├── Intraday Signals
│   └── Day Trading Stats
│
└── Backtest Tab
    ├── Swing Strategy Backtest
    └── Day Strategy Backtest
```

---

## Data Challenges & Solutions

| Challenge | Solution |
|-----------|----------|
| yfinance 5m data limited to 60 days | Cache continuously; use multiple providers |
| Rate limits on intraday data | Implement backoff; cache aggressively |
| Real-time data delays | Accept 5-15 min delay for paper trading |
| After-hours data | Filter to market hours (9:30-16:00 ET) |
| Market holidays | Check calendar before trading |

---

## Implementation Plan

### Phase 1: Infrastructure (Day 1-2)
- [ ] Update database schema for timeframe tracking
- [ ] Create intraday data ingestion pipeline
- [ ] Add timeframe parameter to all models
- [ ] Test 5m data download and storage

### Phase 2: Day Trading Strategies (Day 3-4)
- [ ] Implement RSI Scalping (5m)
- [ ] Implement EMA Crossover (9/21)
- [ ] Implement VWAP Bounce
- [ ] Backtest all strategies

### Phase 3: Portfolio Split (Day 5)
- [ ] Create MultiTimeframePortfolio class
- [ ] Implement capital allocation (60/40 split)
- [ ] Separate position tracking per timeframe
- [ ] Add day trade auto-close at EOD

### Phase 4: Execution Engine (Day 6)
- [ ] Dual check loop (swing + day)
- [ ] Different check frequencies
- [ ] Time-based restrictions
- [ ] Daily loss circuit breaker

### Phase 5: Dashboard (Day 7)
- [ ] Separate tabs for swing/day trading
- [ ] 5m chart support
- [ ] Intraday performance metrics
- [ ] Today's trade log

---

## Testing Strategy

```python
# Test both timeframes independently
def test_swing_trading():
    # Run on daily data
    # Verify 15-min check frequency
    # Test position holds for days
    pass

def test_day_trading():
    # Run on 5m data
    # Verify 1-min check frequency
    # Test positions close EOD
    pass

def test_capital_allocation():
    # Verify 60/40 split
    # Test that day trades don't exceed 40%
    # Test combined P&L
    pass
```

---

## Questions for Review

1. **Capital Split**: Is 60% swing / 40% day appropriate? Should it be adjustable?

2. **Check Frequency**: Swing every 15 min, Day every 1 min. Should day be more frequent?

3. **Data Provider**: yfinance has limits. Should we add backup (Alpha Vantage, Polygon)?

4. **Position Sizing**: Day trades are 5% vs swing 10%. Is this conservative enough?

5. **Auto-Close**: Close all day positions at 3:45 PM. Should some be held overnight?

6. **Overlap**: What if both swing and day want to trade same stock? Allow or prevent?

7. **Performance Reporting**: Show combined or separate metrics?
