"""Backtest commands."""
import click
import json
from datetime import datetime, timedelta

from cli.utils import (
    api_request, print_success, print_error, print_info, print_warning,
    format_table, format_currency, format_percentage, print_panel
)


@click.group()
def backtest():
    """Backtest and strategy testing commands."""
    pass


@backtest.command(name='run')
@click.option('--strategy', '-s', required=True, help='Strategy name (rsi, ma_crossover)')
@click.option('--symbol', '-S', required=True, help='Stock symbol to backtest')
@click.option('--days', '-d', default=180, help='Number of days to backtest')
@click.option('--initial-cash', '-c', default=100000, help='Initial cash for backtest')
@click.option('--start-date', help='Start date (YYYY-MM-DD, overrides --days)')
@click.option('--end-date', help='End date (YYYY-MM-DD)')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']), default='table', help='Output format')
def run(strategy, symbol, days, initial_cash, start_date, end_date, output_format):
    """
    Run a backtest for a strategy on a symbol.
    
    Examples:
        trademind backtest run --strategy rsi --symbol AAPL --days 180
        trademind backtest run -s ma_crossover -S MSFT -d 365 -c 50000
    """
    print()
    print(f"🧪 RUNNING BACKTEST")
    print("═" * 50)
    print()
    print(f"  Strategy:     {strategy}")
    print(f"  Symbol:       {symbol.upper()}")
    print(f"  Period:       {days} days" if not start_date else f"  Start:        {start_date}")
    if end_date:
        print(f"  End:          {end_date}")
    print(f"  Initial Cash: {format_currency(initial_cash)}")
    print()
    
    print_info("Fetching data and running backtest...")
    
    # Build request
    request_data = {
        "symbol": symbol.upper(),
        "strategy": strategy,
        "initial_cash": initial_cash
    }
    
    if start_date:
        request_data["start_date"] = start_date
    if end_date:
        request_data["end_date"] = end_date
    
    data = api_request(
        "POST",
        "/api/strategies/backtest",
        json_data=request_data
    )
    
    if not data:
        return
    
    if output_format == 'json':
        print(json.dumps(data, indent=2))
        return
    
    # Display results
    print()
    print_success("✅ BACKTEST COMPLETE")
    print()
    
    # Calculate derived metrics
    initial_value = data.get('initial_value', initial_cash)
    final_value = data.get('final_value', initial_cash)
    total_return = data.get('total_return', 0)
    total_return_pct = data.get('total_return_pct', 0)
    
    print(f"  Total Return:     {format_currency(total_return)} ({format_percentage(total_return_pct)})")
    print(f"  Final Value:      {format_currency(final_value)}")
    print()
    
    # Trade statistics
    total_trades = data.get('total_trades', 0)
    winning_trades = data.get('winning_trades', 0)
    losing_trades = data.get('losing_trades', 0)
    
    print(f"  Trades:           {total_trades}")
    print(f"  Win Rate:         {format_percentage((winning_trades / total_trades * 100) if total_trades else 0)}")
    print(f"  ({winning_trades} wins, {losing_trades} losses)")
    print()
    
    # Risk metrics
    max_drawdown = data.get('max_drawdown', 0)
    sharpe_ratio = data.get('sharpe_ratio', 0)
    
    print(f"  Max Drawdown:     {format_percentage(max_drawdown)}")
    print(f"  Sharpe Ratio:     {sharpe_ratio:.2f}")
    print()
    
    # Profit factor
    profit_factor = data.get('profit_factor', 0)
    if profit_factor:
        print(f"  Profit Factor:    {profit_factor:.2f}")
    
    # Store trade list if available
    trades = data.get('trades', [])
    if trades and click.confirm("\nView trade details?"):
        print()
        print("📝 TRADES:")
        print("-" * 50)
        
        rows = []
        for trade in trades:
            rows.append([
                trade.get('type', ''),
                trade.get('date', '')[:10],
                format_currency(trade.get('price', 0)),
                trade.get('shares', 0),
                format_currency(trade.get('value', 0))
            ])
        
        headers = ["Type", "Date", "Price", "Shares", "Value"]
        print(format_table(rows[:20], headers))  # Show first 20
        
        if len(trades) > 20:
            print(f"\n... and {len(trades) - 20} more trades")


@backtest.command(name='compare')
@click.option('--strategies', '-s', required=True, help='Comma-separated strategy names')
@click.option('--symbol', '-S', required=True, help='Stock symbol')
@click.option('--days', '-d', default=180, help='Number of days')
@click.option('--initial-cash', '-c', default=100000, help='Initial cash')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']), default='table', help='Output format')
def compare(strategies, symbol, days, initial_cash, output_format):
    """Compare multiple strategies on the same symbol."""
    strategy_list = [s.strip() for s in strategies.split(',')]
    
    print()
    print(f"🧪 COMPARING STRATEGIES")
    print("═" * 50)
    print()
    print(f"  Symbol:       {symbol.upper()}")
    print(f"  Strategies:   {', '.join(strategy_list)}")
    print(f"  Period:       {days} days")
    print()
    
    results = []
    
    for strat in strategy_list:
        print_info(f"Backtesting {strat}...")
        
        data = api_request(
            "POST",
            "/api/strategies/backtest",
            json_data={
                "symbol": symbol.upper(),
                "strategy": strat,
                "initial_cash": initial_cash
            }
        )
        
        if data:
            results.append({
                'strategy': strat,
                'return_pct': data.get('total_return_pct', 0),
                'trades': data.get('total_trades', 0),
                'win_rate': (data.get('winning_trades', 0) / data.get('total_trades', 1) * 100) if data.get('total_trades') else 0,
                'max_drawdown': data.get('max_drawdown', 0),
                'sharpe': data.get('sharpe_ratio', 0)
            })
    
    if not results:
        print_error("❌ No backtest results available")
        return
    
    if output_format == 'json':
        print(json.dumps(results, indent=2))
        return
    
    print()
    print("📊 COMPARISON RESULTS")
    print("═" * 80)
    
    # Sort by return
    results.sort(key=lambda x: x['return_pct'], reverse=True)
    
    rows = []
    for r in results:
        rows.append([
            r['strategy'],
            format_percentage(r['return_pct']),
            r['trades'],
            format_percentage(r['win_rate']),
            format_percentage(r['max_drawdown']),
            f"{r['sharpe']:.2f}"
        ])
    
    headers = ["Strategy", "Return", "Trades", "Win Rate", "Max DD", "Sharpe"]
    print(format_table(rows, headers))
    
    print()
    print(f"🏆 Best Strategy: {results[0]['strategy']} ({format_percentage(results[0]['return_pct'])})")


@backtest.command(name='list')
@click.option('--limit', '-n', default=10, help='Number of backtests to show')
def list_backtests(limit):
    """List recent backtests (stored locally)."""
    # This would require storing backtests to database
    # For now, show placeholder
    print_info("Backtest history storage not yet implemented")
    print()
    print("Recent backtests are shown when you run them.")
    print("Use 'trademind backtest run' to execute a new backtest.")


@backtest.command()
@click.argument('backtest_id')
def results(backtest_id):
    """View backtest results by ID."""
    print_info("Backtest result storage not yet implemented")
    print()
    print("Use 'trademind backtest run' to see results immediately.")


@backtest.command()
@click.argument('backtest_id')
@click.option('--format', type=click.Choice(['csv', 'json']), default='json', help='Export format')
@click.option('--output', '-o', help='Output file')
def export(backtest_id, format, output):
    """Export backtest results."""
    print_info("Backtest export not yet implemented")
