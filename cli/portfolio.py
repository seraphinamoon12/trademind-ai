"""Portfolio management commands."""
import click
import json
from datetime import datetime, timedelta

from cli.utils import (
    api_request, print_success, print_error, print_info, print_warning,
    format_table, format_currency, format_percentage, print_panel
)


@click.group()
def portfolio():
    """Portfolio management commands."""
    pass


@portfolio.command()
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']), default='table', help='Output format')
def holdings(output_format):
    """Show detailed holdings."""
    data = api_request("GET", "/api/portfolio/holdings")
    
    if not data:
        return
    
    if output_format == 'json':
        print(json.dumps(data, indent=2))
        return
    
    if not data:
        print_info("📭 No holdings")
        return
    
    # Format holdings table
    rows = []
    total_value = 0
    total_cost = 0
    
    for symbol, position in data.items():
        current_price = position.get('current_price', 0)
        quantity = position.get('quantity', 0)
        avg_cost = position.get('avg_cost', 0)
        
        market_value = current_price * quantity
        cost_basis = avg_cost * quantity
        unrealized_pnl = market_value - cost_basis
        pnl_pct = (unrealized_pnl / cost_basis * 100) if cost_basis else 0
        
        total_value += market_value
        total_cost += cost_basis
        
        # Add emoji for P&L
        pnl_emoji = "🟢" if unrealized_pnl >= 0 else "🔴"
        
        rows.append([
            symbol,
            quantity,
            format_currency(avg_cost),
            format_currency(current_price),
            format_currency(market_value),
            f"{format_percentage(unrealized_pnl)} {pnl_emoji}",
            format_percentage(pnl_pct)
        ])
    
    # Sort by market value descending
    rows.sort(key=lambda x: float(x[4].replace('$', '').replace(',', '')), reverse=True)
    
    headers = ["Symbol", "Qty", "Avg Cost", "Current", "Value", "P&L ($)", "P&L (%)"]
    
    print_panel(
        format_table(rows, headers),
        title="📊 Holdings"
    )
    
    # Summary
    total_pnl = total_value - total_cost
    print(f"\nTotal Value: {format_currency(total_value)}")
    print(f"Total P&L: {format_percentage(total_pnl / total_cost * 100) if total_cost else '+0.00%'}")


@portfolio.command()
@click.option('--days', default=30, help='Number of days for performance')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']), default='table', help='Output format')
def performance(days, output_format):
    """View portfolio performance over time."""
    data = api_request("GET", "/api/portfolio/performance", params={"days": days})
    
    if not data:
        return
    
    snapshots = data.get('snapshots', [])
    
    if not snapshots:
        print_warning(f"⚠️  No performance data for last {days} days")
        return
    
    if output_format == 'json':
        print(json.dumps(data, indent=2))
        return
    
    rows = []
    for snap in snapshots:
        timestamp = snap.get('timestamp', '')[:10]  # Just the date
        total_value = snap.get('total_value', 0)
        total_return_pct = snap.get('total_return_pct', 0)
        
        rows.append([
            timestamp,
            format_currency(total_value),
            format_percentage(total_return_pct)
        ])
    
    headers = ["Date", "Total Value", "Return (%)"]
    
    print_panel(
        format_table(rows, headers),
        title=f"📈 Performance (Last {days} Days)"
    )


@portfolio.command(name='list')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']), default='table', help='Output format')
def list_portfolio(output_format):
    """Show portfolio summary and holdings."""
    data = api_request("GET", "/api/portfolio/")
    
    if not data:
        return
    
    if output_format == 'json':
        print(json.dumps(data, indent=2))
        return
    
    portfolio = data.get('portfolio', {})
    holdings = data.get('holdings', {})
    
    # Summary
    total_value = portfolio.get('total_value', 0)
    cash_balance = portfolio.get('cash_balance', 0)
    invested_value = portfolio.get('invested_value', 0)
    total_return = portfolio.get('total_return', 0)
    total_return_pct = portfolio.get('total_return_pct', 0)
    
    print()
    print("╔══════════════════════════════════════════════════╗")
    print("║           📊 PORTFOLIO SUMMARY                   ║")
    print("╚══════════════════════════════════════════════════╝")
    print()
    
    print(f"  Total Value:     {format_currency(total_value):>18}")
    print(f"  Cash Balance:    {format_currency(cash_balance):>18}")
    print(f"  Invested:        {format_currency(invested_value):>18}")
    print()
    
    return_emoji = "🟢" if total_return >= 0 else "🔴"
    print(f"  Total Return:    {format_currency(total_return):>18} {return_emoji}")
    print(f"  Return %:        {format_percentage(total_return_pct):>18}")
    print()
    
    # Holdings summary
    if holdings:
        print("  ─────── Holdings ───────────────────────────────")
        print()
        
        rows = []
        for symbol, position in holdings.items():
            qty = position.get('quantity', 0)
            price = position.get('current_price', 0)
            value = qty * price
            rows.append([symbol, qty, format_currency(price), format_currency(value)])
        
        # Sort by value
        rows.sort(key=lambda x: float(x[3].replace('$', '').replace(',', '')), reverse=True)
        
        for row in rows[:5]:  # Top 5
            print(f"    {row[0]:<6} {row[1]:>6} @ {row[2]:>10} = {row[3]:>12}")
        
        if len(rows) > 5:
            print(f"    ... and {len(rows) - 5} more positions")
    else:
        print("  📭 No holdings")
    
    print()


@portfolio.command()
def update_prices():
    """Update prices for all holdings."""
    print_info("🔄 Updating prices...")
    
    data = api_request("POST", "/api/portfolio/update-prices")
    
    if data:
        updated = data.get('updated', 0)
        prices = data.get('prices', {})
        
        print_success(f"✅ Updated {updated} prices")
        
        if prices:
            rows = [[symbol, format_currency(price)] for symbol, price in prices.items()]
            headers = ["Symbol", "Price"]
            print()
            print(format_table(rows, headers))


# Default command when just 'portfolio' is called
@portfolio.command(name='summary')
def summary():
    """Portfolio summary (default)."""
    ctx = click.get_current_context()
    ctx.invoke(list_portfolio, output_format='table')


# Set default command
portfolio.default_command = summary
