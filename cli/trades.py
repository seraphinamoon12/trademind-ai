"""Trade history and management commands."""
import click
import json
from datetime import datetime, timedelta

from cli.utils import (
    api_request, print_success, print_error, print_info, print_warning,
    format_table, format_currency, format_percentage
)


@click.group()
def trades():
    """Trade history and management commands."""
    pass


@trades.command(name='list')
@click.option('--limit', '-n', default=50, help='Number of trades to show')
@click.option('--symbol', '-s', help='Filter by symbol')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']), default='table', help='Output format')
def list_trades(limit, symbol, output_format):
    """List recent trades."""
    params = {"limit": limit}
    if symbol:
        params["symbol"] = symbol.upper()
    
    data = api_request("GET", "/api/trades/", params=params)
    
    if not data:
        return
    
    trades = data.get('trades', [])
    
    if not trades:
        print_info("📭 No trades found")
        return
    
    if output_format == 'json':
        print(json.dumps(data, indent=2))
        return
    
    rows = []
    for trade in trades:
        trade_id = trade.get('id', '')
        timestamp = trade.get('timestamp', '')
        
        # Format timestamp
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            time_str = dt.strftime("%Y-%m-%d %H:%M")
        except:
            time_str = timestamp[:16] if timestamp else ""
        
        symbol = trade.get('symbol', '')
        action = trade.get('action', '')
        quantity = trade.get('quantity', 0)
        price = trade.get('price', 0)
        total_value = trade.get('total_value', 0)
        strategy = trade.get('strategy', '')
        confidence = trade.get('confidence')
        
        # Action emoji
        action_emoji = "🟢" if action == "BUY" else "🔴" if action == "SELL" else "⚪"
        
        rows.append([
            trade_id,
            symbol,
            f"{action_emoji} {action}",
            quantity,
            format_currency(price),
            format_currency(total_value),
            strategy[:15],
            time_str
        ])
    
    headers = ["ID", "Symbol", "Action", "Qty", "Price", "Total", "Strategy", "Time"]
    
    print()
    print(f"📝 Recent Trades (showing {len(trades)})")
    print("=" * 80)
    print(format_table(rows, headers))


@trades.command()
@click.option('--symbol', '-s', help='Filter by symbol')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']), default='table', help='Output format')
def today(symbol, output_format):
    """View today's trades."""
    # Get trades from today by filtering
    params = {"limit": 100}
    if symbol:
        params["symbol"] = symbol.upper()
    
    data = api_request("GET", "/api/trades/", params=params)
    
    if not data:
        return
    
    all_trades = data.get('trades', [])
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    # Filter for today
    trades = [
        t for t in all_trades 
        if t.get('timestamp', '').startswith(today_str)
    ]
    
    if not trades:
        print_info(f"📭 No trades today ({today_str})")
        return
    
    if output_format == 'json':
        print(json.dumps({"trades": trades}, indent=2))
        return
    
    rows = []
    for trade in trades:
        action_emoji = "🟢" if trade.get('action') == "BUY" else "🔴"
        rows.append([
            trade.get('symbol', ''),
            f"{action_emoji} {trade.get('action', '')}",
            trade.get('quantity', 0),
            format_currency(trade.get('price', 0)),
            format_currency(trade.get('total_value', 0)),
            trade.get('strategy', '')
        ])
    
    headers = ["Symbol", "Action", "Qty", "Price", "Total", "Strategy"]
    
    print()
    print(f"📅 Today's Trades ({today_str}) - {len(trades)} trades")
    print("=" * 60)
    print(format_table(rows, headers))


@trades.command()
@click.option('--symbol', '-s', help='Filter by symbol')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']), default='table', help='Output format')
def pnl(symbol, output_format):
    """View P&L by symbol."""
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
    
    # Calculate P&L by symbol
    symbol_pnl = {}
    
    for trade in trades:
        sym = trade.get('symbol', '')
        action = trade.get('action', '')
        total_value = trade.get('total_value', 0)
        
        if sym not in symbol_pnl:
            symbol_pnl[sym] = {"buys": 0, "sells": 0, "pnl": 0, "trades": 0}
        
        symbol_pnl[sym]["trades"] += 1
        
        if action == "BUY":
            symbol_pnl[sym]["buys"] += total_value
        elif action == "SELL":
            symbol_pnl[sym]["sells"] += total_value
    
    # Simple P&L calculation (sells - buys)
    # Note: This is simplified; real P&L requires matching trades
    for sym in symbol_pnl:
        data = symbol_pnl[sym]
        data["pnl"] = data["sells"] - data["buys"]
        data["invested"] = data["buys"]
    
    if output_format == 'json':
        print(json.dumps(symbol_pnl, indent=2))
        return
    
    rows = []
    for sym, data in sorted(symbol_pnl.items(), key=lambda x: x[1]["pnl"], reverse=True):
        pnl_value = data["pnl"]
        pnl_emoji = "🟢" if pnl_value >= 0 else "🔴"
        
        rows.append([
            sym,
            data["trades"],
            format_currency(data["invested"]),
            f"{pnl_emoji} {format_currency(pnl_value)}",
            format_percentage(pnl_value / data["invested"] * 100) if data["invested"] else "0.00%"
        ])
    
    headers = ["Symbol", "Trades", "Invested", "Realized P&L", "Return %"]
    
    print()
    print("💰 P&L by Symbol")
    print("=" * 70)
    print(format_table(rows, headers))


@trades.command()
@click.argument('trade_id', type=int)
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']), default='table', help='Output format')
def show(trade_id, output_format):
    """View trade details by ID."""
    # Get all trades and find the one with matching ID
    data = api_request("GET", "/api/trades/", params={"limit": 1000})
    
    if not data:
        return
    
    trades = data.get('trades', [])
    trade = next((t for t in trades if t.get('id') == trade_id), None)
    
    if not trade:
        print_error(f"❌ Trade {trade_id} not found")
        return
    
    if output_format == 'json':
        print(json.dumps(trade, indent=2))
        return
    
    print()
    print(f"📝 Trade Details - ID: {trade_id}")
    print("=" * 50)
    
    for key, value in trade.items():
        if key in ['price', 'total_value'] and value is not None:
            value = format_currency(value)
        elif key in ['confidence'] and value is not None:
            value = f"{value:.2%}"
        print(f"  {key.replace('_', ' ').title():<15}: {value}")


@trades.command()
@click.option('--start', help='Start date (YYYY-MM-DD)')
@click.option('--end', help='End date (YYYY-MM-DD)')
@click.option('--format', 'output_format', type=click.Choice(['csv', 'json']), default='json', help='Export format')
@click.option('--output', '-o', help='Output file path')
def export(start, end, output_format, output):
    """Export trade history."""
    params = {"limit": 1000}
    
    data = api_request("GET", "/api/trades/", params=params)
    
    if not data:
        return
    
    trades = data.get('trades', [])
    
    # Filter by date if provided
    if start:
        trades = [t for t in trades if t.get('timestamp', '') >= start]
    if end:
        trades = [t for t in trades if t.get('timestamp', '') <= f"{end}T23:59:59"]
    
    if not trades:
        print_warning("⚠️  No trades in date range")
        return
    
    if output_format == 'json':
        content = json.dumps({"trades": trades}, indent=2)
    else:
        # CSV format
        import csv
        import io
        
        output_buffer = io.StringIO()
        if trades:
            writer = csv.DictWriter(output_buffer, fieldnames=trades[0].keys())
            writer.writeheader()
            writer.writerows(trades)
        content = output_buffer.getvalue()
    
    if output:
        with open(output, 'w') as f:
            f.write(content)
        print_success(f"✅ Exported {len(trades)} trades to {output}")
    else:
        print(content)
