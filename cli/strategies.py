"""Strategy management commands."""
import click
import json

from cli.utils import (
    api_request, print_success, print_error, print_info, print_warning,
    format_table, format_percentage, status_emoji
)


@click.group()
def strategies():
    """Strategy management commands."""
    pass


@strategies.command(name='list')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']), default='table', help='Output format')
def list_strategies(output_format):
    """List all available strategies."""
    data = api_request("GET", "/api/strategies/")
    
    if not data:
        return
    
    strategies = data.get('strategies', [])
    
    if not strategies:
        print_warning("⚠️  No strategies found")
        return
    
    if output_format == 'json':
        print(json.dumps(data, indent=2))
        return
    
    rows = []
    for strat in strategies:
        name = strat.get('name', '')
        description = strat.get('description', '')
        params = strat.get('parameters', {})
        
        # Format parameters
        params_str = ", ".join([f"{k}={v}" for k, v in params.items()])
        
        # Default status - in a real implementation, this would come from API
        status = "✅ ON"  # Placeholder
        
        rows.append([
            name,
            status,
            description[:40] + "..." if len(description) > 40 else description,
            params_str[:30] + "..." if len(params_str) > 30 else params_str
        ])
    
    headers = ["Name", "Status", "Description", "Parameters"]
    
    print()
    print("⚙️  Trading Strategies")
    print("=" * 80)
    print(format_table(rows, headers))


@strategies.command()
@click.argument('strategy_name')
@click.option('--symbol', '-s', default='AAPL', help='Symbol to analyze')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']), default='table', help='Output format')
def signal(strategy_name, symbol, output_format):
    """Get current signal for a symbol using a strategy."""
    print_info(f"🔍 Getting {strategy_name} signal for {symbol.upper()}...")
    
    data = api_request(
        "POST", 
        "/api/strategies/signal",
        params={"symbol": symbol.upper(), "strategy": strategy_name}
    )
    
    if not data:
        return
    
    if output_format == 'json':
        print(json.dumps(data, indent=2))
        return
    
    symbol = data.get('symbol', '')
    signal = data.get('signal', 'HOLD')
    confidence = data.get('confidence', 0)
    price = data.get('price', 0)
    metadata = data.get('metadata', {})
    
    # Signal emoji
    signal_emoji = {
        'BUY': '🟢',
        'SELL': '🔴',
        'HOLD': '⚪'
    }.get(signal, '⚪')
    
    print()
    print(f"📊 Strategy Signal: {strategy_name.upper()}")
    print("=" * 50)
    print(f"  Symbol:     {symbol}")
    print(f"  Signal:     {signal_emoji} {signal}")
    print(f"  Confidence: {confidence:.2%}")
    print(f"  Price:      ${price:.2f}")
    
    if metadata:
        print()
        print("  Metadata:")
        for key, value in metadata.items():
            print(f"    {key}: {value}")


@strategies.command()
@click.argument('strategy_name')
def enable(strategy_name):
    """Enable a trading strategy."""
    print_info(f"🟢 Enabling strategy: {strategy_name}")
    
    # In a real implementation, this would call an API endpoint
    # For now, we display a message
    print_warning("⚠️  Strategy enable/disable requires agent orchestrator update")
    print_info("   Strategies are currently managed through the agent configuration")


@strategies.command()
@click.argument('strategy_name')
def disable(strategy_name):
    """Disable a trading strategy."""
    print_info(f"🔴 Disabling strategy: {strategy_name}")
    
    # In a real implementation, this would call an API endpoint
    print_warning("⚠️  Strategy enable/disable requires agent orchestrator update")
    print_info("   Strategies are currently managed through the agent configuration")


@strategies.command()
@click.argument('strategy_name')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']), default='table', help='Output format')
def config(strategy_name, output_format):
    """View strategy configuration."""
    data = api_request("GET", "/api/strategies/")
    
    if not data:
        return
    
    strategies = data.get('strategies', [])
    strategy = next((s for s in strategies if s.get('name') == strategy_name), None)
    
    if not strategy:
        print_error(f"❌ Strategy '{strategy_name}' not found")
        return
    
    if output_format == 'json':
        print(json.dumps(strategy, indent=2))
        return
    
    print()
    print(f"⚙️  Strategy Configuration: {strategy_name}")
    print("=" * 50)
    
    for key, value in strategy.items():
        if key == 'parameters':
            print(f"\n  {key.title()}:")
            for param, val in value.items():
                print(f"    {param}: {val}")
        else:
            print(f"  {key.title()}: {value}")


@strategies.command()
@click.option('--symbol', '-s', help='Filter by symbol')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']), default='table', help='Output format')
def performance(symbol, output_format):
    """View strategy performance."""
    # Get trades to calculate strategy performance
    params = {"limit": 500}
    if symbol:
        params["symbol"] = symbol.upper()
    
    data = api_request("GET", "/api/trades/", params=params)
    
    if not data:
        return
    
    trades = data.get('trades', [])
    
    if not trades:
        print_info("📭 No trades found")
        return
    
    # Calculate performance by strategy
    strategy_stats = {}
    
    for trade in trades:
        strat = trade.get('strategy', 'unknown')
        
        if strat not in strategy_stats:
            strategy_stats[strat] = {
                "trades": 0,
                "wins": 0,
                "losses": 0,
                "total_pnl": 0
            }
        
        strategy_stats[strat]["trades"] += 1
    
    # Note: Real win/loss calculation requires matching buy/sell pairs
    # This is a simplified version
    
    if output_format == 'json':
        print(json.dumps(strategy_stats, indent=2))
        return
    
    rows = []
    for strat, stats in strategy_stats.items():
        rows.append([
            strat,
            stats["trades"],
            stats["wins"],
            stats["losses"],
            format_percentage(stats["wins"] / stats["trades"] * 100) if stats["trades"] else "0.00%"
        ])
    
    headers = ["Strategy", "Trades", "Wins", "Losses", "Win Rate"]
    
    print()
    print("📈 Strategy Performance")
    print("=" * 60)
    print(format_table(rows, headers))
    print()
    print("Note: Win/loss requires matching buy/sell pairs. Basic stats shown.")


@strategies.command()
@click.argument('strategy_name')
@click.option('--symbol', '-s', required=True, help='Symbol to backtest')
@click.option('--days', '-d', default=180, help='Number of days to backtest')
@click.option('--initial-cash', default=100000, help='Initial cash for backtest')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']), default='table', help='Output format')
def backtest(strategy_name, symbol, days, initial_cash, output_format):
    """Backtest a strategy (shortcut to backtest command)."""
    from cli.backtest import run
    ctx = click.get_current_context()
    ctx.invoke(run, strategy=strategy_name, symbol=symbol, days=days, 
               initial_cash=initial_cash, output_format=output_format)
