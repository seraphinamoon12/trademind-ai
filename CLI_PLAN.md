# CLI Control Plan - TradeMind AI

## Overview

Command-line interface for managing the TradeMind AI trading agent without using the web dashboard. Essential for automation, scripting, and remote server management.

---

## CLI Architecture

```
 trademind [command] [subcommand] [options]
 
 Commands:
 ├── server       # Server management
 ├── portfolio    # Portfolio viewing
 ├── trades       # Trade history
 ├── strategies   # Strategy management
 ├── safety       # Safety/risk controls
 ├── backtest     # Run backtests
 ├── data         # Data management
 └── config       # Configuration
```

---

## Installation

```bash
# Make CLI available globally
pip install -e ~/projects/trading-agent

# Or run directly
python -m trademind [command]
```

---

## Commands

### 1. Server Management

```bash
# Start the trading server
trademind server start [--port 8000] [--reload]

# Stop the trading server
trademind server stop

# Check server status
trademind server status

# View server logs
trademind server logs [--follow] [--lines 100]

# Restart server
trademind server restart
```

**Implementation:**
```python
@click.group()
def server():
    """Server management commands"""
    pass

@server.command()
@click.option('--port', default=8000, help='Server port')
@click.option('--reload', is_flag=True, help='Auto-reload on code changes')
def start(port, reload):
    """Start the trading server"""
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=port, reload=reload)

@server.command()
def stop():
    """Stop the trading server"""
    # Read PID from file and kill
    pid_file = Path("server.pid")
    if pid_file.exists():
        pid = int(pid_file.read_text())
        os.kill(pid, signal.SIGTERM)
        click.echo("✓ Server stopped")
    else:
        click.echo("✗ Server not running")

@server.command()
def status():
    """Check server status"""
    try:
        response = requests.get("http://localhost:8000/health")
        if response.status_code == 200:
            data = response.json()
            click.echo(f"✓ Server running")
            click.echo(f"  App: {data['app']}")
            click.echo(f"  Status: {data['status']}")
        else:
            click.echo("✗ Server unhealthy")
    except:
        click.echo("✗ Server not responding")
```

---

### 2. Portfolio Commands

```bash
# View current portfolio
trademind portfolio

# Show detailed holdings
trademind portfolio holdings

# View performance metrics
trademind portfolio performance [--days 30]

# View sector allocation
trademind portfolio sectors

# Export portfolio data
trademind portfolio export [--format csv|json] [--output file.csv]
```

**Example Output:**
```
$ trademind portfolio

📊 Portfolio Summary
═══════════════════════════════════════
Total Value:     $102,456.78 (+2.46%)
Cash Balance:    $45,000.00
Invested:        $57,456.78
Daily P&L:       +$234.56 (+0.23%)
Total Return:    +$2,456.78 (+2.46%)

Open Positions:  3 / 5 max
Portfolio Heat:  4.2% / 10% max

Top Holdings:
  AAPL    $12,450.00  (+5.2%)  🟢
  MSFT    $23,100.00  (+1.8%)  🟢
  TSLA    $21,906.78  (-2.1%)  🔴
```

---

### 3. Trade Commands

```bash
# List recent trades
trademind trades list [--limit 20] [--symbol AAPL]

# View trade details
trademind trades show [trade_id]

# Export trade history
trademind trades export [--start 2024-01-01] [--end 2024-02-01]

# View today's trades
trademind trades today

# View P&L by symbol
trademind trades pnl [--symbol AAPL]
```

**Example Output:**
```
$ trademind trades list --limit 5

📝 Recent Trades
═══════════════════════════════════════
ID      Symbol  Action  Price      P&L       Strategy    Time
─────────────────────────────────────────────────────────────────
1042    AAPL    BUY     $185.50    -         RSI         2h ago
1041    MSFT    SELL    $412.30    +$234.50  MA Cross    5h ago
1040    TSLA    BUY     $242.10    -         RSI         1d ago
1039    NVDA    SELL    $875.20    +$156.80  MA Cross    2d ago
1038    META    BUY     $485.60    -         RSI         2d ago
```

---

### 4. Strategy Commands

```bash
# List all strategies
trademind strategies list

# Enable/disable strategy
trademind strategies enable rsi
trademind strategies disable ma_crossover

# View strategy configuration
trademind strategies config rsi

# Update strategy parameter
trademind strategies set rsi --oversold 25 --overbought 75

# View strategy performance
trademind strategies performance [--strategy rsi]

# Backtest strategy
trademind strategies backtest rsi --symbol AAPL --days 180
```

**Example Output:**
```
$ trademind strategies list

⚙️  Trading Strategies
═══════════════════════════════════════
Name            Status    Win Rate    Profit Factor    Trades
─────────────────────────────────────────────────────────────
rsi_reversion   ✅ ON      42.3%       1.45             156
ma_crossover    ✅ ON      38.7%       1.32             203
─────────────────────────────────────────────────────────────

$ trademind strategies performance

📈 Strategy Performance (Last 30 Days)
═══════════════════════════════════════
RSI Reversion:
  Win Rate:      45.2%
  Avg Win:       +$245.60
  Avg Loss:      -$112.30
  Profit Factor: 1.58
  Total Trades:  42

MA Crossover:
  Win Rate:      38.9%
  Avg Win:       +$189.40
  Avg Loss:      -$98.50
  Profit Factor: 1.41
  Total Trades:  54
```

---

### 5. Safety Commands

```bash
# View safety status
trademind safety status

# View circuit breaker status
trademind safety circuit-breaker

# View portfolio heat
trademind safety heat

# EMERGENCY: Stop all trading
trademind safety emergency-stop [--reason "Manual halt"]

# Reset circuit breaker (manual override)
trademind safety reset-circuit-breaker

# View risk limits
trademind safety limits

# Update risk parameter
trademind safety set --max-positions 8
```

**Example Output:**
```
$ trademind safety status

🛡️  Safety Status
═══════════════════════════════════════
Circuit Breaker:  🟢 ARMED
Daily P&L:        +0.23% / -3.0% limit
Drawdown:         -2.1% / -15% limit
Consecutive Loss: 1 / 5 limit
Status:           ✅ Trading allowed

Portfolio Heat:
  Current Heat:   4.2% / 10% max
  Risk Amount:    $4,200
  Max Risk:       $10,000

Open Positions:   3 / 5 max

$ trademind safety emergency-stop --reason "Market volatility"
🚨 EMERGENCY STOP TRIGGERED
═══════════════════════════════════════
All trading halted.
Reason: Market volatility
Time: 2024-02-07 14:32:15 EST

Positions remain open. Manual review required.
```

---

### 6. Backtest Commands

```bash
# Run backtest
trademind backtest run --strategy rsi --symbol AAPL --days 180

# Run backtest for multiple symbols
trademind backtest run --strategy ma --symbols AAPL,MSFT,TSLA --days 90

# Compare strategies
trademind backtest compare --strategies rsi,ma --symbol AAPL

# View backtest results
trademind backtest results [backtest_id]

# List recent backtests
trademind backtest list [--limit 10]

# Export backtest results
trademind backtest export [backtest_id] --format csv
```

**Example Output:**
```
$ trademind backtest run --strategy rsi --symbol AAPL --days 180

🧪 Running Backtest
═══════════════════════════════════════
Strategy:    RSI Mean Reversion
Symbol:      AAPL
Period:      180 days
Capital:     $100,000

Results:
  Total Return:    +12.45%
  Max Drawdown:    -4.23%
  Sharpe Ratio:    1.34
  Win Rate:        43.2%
  Profit Factor:   1.52
  Trades:          28

✓ Backtest complete. ID: bt_20240207_143022
```

---

### 7. Data Commands

```bash
# Ingest data for symbols
trademind data ingest --symbols AAPL,MSFT,TSLA

# Check data status
trademind data status

# View data for symbol
trademind data show AAPL [--days 30]

# Update indicators
trademind data update-indicators

# Clear cache
trademind data clear-cache

# Verify data quality
trademind data verify
```

---

### 8. Config Commands

```bash
# View current config
trademind config show

# Get specific config value
trademind config get trading.starting_capital

# Set config value
trademind config set trading.max_position_pct 0.12

# Reset to defaults
trademind config reset

# Validate config
trademind config validate

# Export config
trademind config export > trademind_config.yaml

# Import config
trademind config import trademind_config.yaml
```

---

## Interactive Mode

```bash
# Enter interactive shell
$ trademind shell

trademind> portfolio
[shows portfolio]

trademind> trades today
[shows today's trades]

trademind> safety status
[shows safety status]

trademind> exit
```

---

## Automation Examples

### Cron Job - Daily Report
```bash
# Add to crontab
0 17 * * * trademind portfolio --format json > /var/log/trademind/daily_$(date +\%Y\%m\%d).json
```

### Script - Strategy Rotation
```bash
#!/bin/bash
# Disable underperforming strategies

WIN_RATE=$(trademind strategies performance --strategy rsi --format json | jq '.win_rate')
if (( $(echo "$WIN_RATE < 0.30" | bc -l) )); then
    trademind strategies disable rsi
    echo "RSI strategy disabled - win rate $WIN_RATE"
fi
```

### Health Check
```bash
#!/bin/bash
# Check if server is healthy, restart if not

if ! trademind server status | grep -q "running"; then
    trademind server restart
    echo "$(date): Server restarted" >> /var/log/trademind/restarts.log
fi
```

---

## Implementation

### File Structure
```
trading-agent/
├── cli/
│   ├── __init__.py
│   ├── main.py           # Entry point
│   ├── server.py         # Server commands
│   ├── portfolio.py      # Portfolio commands
│   ├── trades.py         # Trade commands
│   ├── strategies.py     # Strategy commands
│   ├── safety.py         # Safety commands
│   ├── backtest.py       # Backtest commands
│   ├── data.py           # Data commands
│   └── config.py         # Config commands
├── setup.py              # CLI installation
└── trademind             # Executable script
```

### Dependencies
```python
# cli/requirements.txt
click>=8.0.0
requests>=2.28.0
tabulate>=0.9.0  # For table formatting
rich>=13.0.0     # For colored output
pyyaml>=6.0      # For config files
```

### Entry Point
```python
# setup.py
setup(
    name="trademind-cli",
    entry_points={
        'console_scripts': [
            'trademind=cli.main:cli',
        ],
    },
)
```

---

## Testing

```bash
# Test CLI commands
python -m pytest tests/cli/test_server.py
python -m pytest tests/cli/test_portfolio.py
python -m pytest tests/cli/test_safety.py
```

---

## Documentation

```bash
# Get help
trademind --help
trademind server --help
trademind portfolio --help

# Get command examples
trademind examples
```

---

## Future Enhancements

1. **WebSocket Mode** - Real-time updates in terminal
2. **Dashboard Mode** - `trademind dashboard` launches TUI
3. **Plugin System** - Custom commands via plugins
4. **Remote Control** - CLI for remote servers via SSH
5. **Notification Integration** - Slack/Discord alerts via CLI

---

## Summary

The CLI provides complete control over TradeMind AI:
- **Server management** - Start/stop/restart
- **Portfolio monitoring** - Holdings, performance, sectors
- **Trade analysis** - History, P&L, exports
- **Strategy control** - Enable/disable, configure, backtest
- **Safety controls** - Circuit breaker, emergency stop, limits
- **Data management** - Ingest, verify, clear cache
- **Configuration** - View, set, validate settings

**All commands work via API** - no direct database access needed.
