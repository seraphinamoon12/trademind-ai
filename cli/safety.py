"""Safety and risk management commands."""
import click
import json

from cli.utils import (
    api_request, print_success, print_error, print_info, print_warning,
    format_table, format_currency, format_percentage, status_emoji, print_panel
)


@click.group()
def safety():
    """Safety and risk management commands."""
    pass


@safety.command()
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']), default='table', help='Output format')
def status(output_format):
    """View complete safety system status."""
    data = api_request("GET", "/api/safety/status")
    
    if not data:
        return
    
    if output_format == 'json':
        print(json.dumps(data, indent=2))
        return
    
    # Parse status
    circuit_breaker = data.get('circuit_breaker', {})
    portfolio_heat = data.get('portfolio_heat', {})
    position_sizing = data.get('position_sizing', {})
    market_status = data.get('market_status', {})
    risk_limits = data.get('risk_limits', {})
    
    print()
    print("🛡️  SAFETY SYSTEM STATUS")
    print("═" * 60)
    print()
    
    # Circuit Breaker
    is_halted = circuit_breaker.get('is_halted', False)
    halt_status = "🚨 HALTED" if is_halted else "🟢 ARMED"
    print(f"  Circuit Breaker:  {halt_status}")
    
    if is_halted:
        print(f"  Halt Reason:      {circuit_breaker.get('halt_reason', 'Unknown')}")
    else:
        daily_pnl = circuit_breaker.get('daily_pnl', 0)
        daily_limit = circuit_breaker.get('daily_loss_limit', -0.03)
        print(f"  Daily P&L:        {format_percentage(daily_pnl)} / {format_percentage(daily_limit)} limit")
    print()
    
    # Portfolio Heat
    current_heat = portfolio_heat.get('current_heat', 0)
    max_heat = portfolio_heat.get('max_heat', 0.10)
    heat_status = "🔴 HIGH" if current_heat >= max_heat * 0.8 else "🟢 OK"
    
    print(f"  Portfolio Heat:   {heat_status}")
    print(f"  Current:          {format_percentage(current_heat)} / {format_percentage(max_heat)} max")
    
    if 'risk_amount' in portfolio_heat:
        print(f"  Risk Amount:      {format_currency(portfolio_heat['risk_amount'])}")
    print()
    
    # Open Positions
    positions = data.get('open_positions', {})
    current_pos = positions.get('current', 0)
    max_pos = positions.get('max', 5)
    print(f"  Open Positions:   {current_pos} / {max_pos} max")
    print()
    
    # Market Status
    if market_status:
        is_open = market_status.get('market_open', False)
        print(f"  Market:           {'🟢 OPEN' if is_open else '🔴 CLOSED'}")
        if 'next_open' in market_status:
            print(f"  Next Open:        {market_status['next_open']}")
    print()
    
    # Overall Status
    trading_allowed = data.get('trading_allowed', True)
    if trading_allowed and not is_halted:
        print("  ✅ Trading Allowed")
    else:
        print("  ❌ Trading Halted")


@safety.command(name='circuit-breaker')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']), default='table', help='Output format')
def circuit_breaker_status(output_format):
    """View circuit breaker status."""
    data = api_request("GET", "/api/safety/circuit-breaker")
    
    if not data:
        return
    
    if output_format == 'json':
        print(json.dumps(data, indent=2))
        return
    
    print()
    print("⚡ CIRCUIT BREAKER STATUS")
    print("═" * 50)
    print()
    
    is_halted = data.get('is_halted', False)
    print(f"  Status:           {'🚨 HALTED' if is_halted else '🟢 ARMED'}")
    
    if data.get('halt_reason'):
        print(f"  Halt Reason:      {data['halt_reason']}")
    
    print(f"  Daily P&L:        {format_percentage(data.get('daily_pnl', 0))}")
    print(f"  Daily Limit:      {format_percentage(data.get('daily_loss_limit', -0.03))}")
    print(f"  Drawdown:         {format_percentage(data.get('drawdown', 0))}")
    print(f"  Drawdown Limit:   {format_percentage(data.get('max_drawdown', -0.15))}")
    print(f"  Consecutive Loss: {data.get('consecutive_losses', 0)} / {data.get('max_consecutive_losses', 5)} max")


@safety.command(name='emergency-stop')
@click.option('--reason', default='Manual halt via CLI', help='Reason for emergency stop')
def emergency_stop(reason):
    """
    EMERGENCY: Stop all trading immediately.
    
    This triggers the circuit breaker and creates a kill switch file.
    All trading will be halted until manually reset.
    """
    print()
    print("🚨 EMERGENCY STOP REQUESTED")
    print("═" * 50)
    print()
    print(f"Reason: {reason}")
    print()
    
    # Confirm
    if not click.confirm("⚠️  Are you sure you want to EMERGENCY STOP all trading?"):
        print("Cancelled.")
        return
    
    print()
    print("Triggering emergency stop...")
    
    data = api_request(
        "POST", 
        "/api/safety/emergency/stop",
        json_data={"reason": reason}
    )
    
    if data:
        print()
        print_success("✅ EMERGENCY STOP TRIGGERED")
        print()
        print(f"Status:       {data.get('status', 'halted')}")
        print(f"Reason:       {data.get('reason', reason)}")
        print(f"Kill Switch:  {data.get('kill_switch_file', 'N/A')}")
        print(f"Timestamp:    {data.get('timestamp', '')}")
        print()
        print("All trading has been halted. Manual review required.")
        print("Use 'trademind safety reset-circuit-breaker' to resume.")


@safety.command(name='reset-circuit-breaker')
def reset_circuit_breaker():
    """Reset the circuit breaker after it's been triggered."""
    print()
    print("🔄 RESET CIRCUIT BREAKER")
    print("═" * 50)
    print()
    
    # Check current status
    status_data = api_request("GET", "/api/safety/circuit-breaker")
    
    if not status_data:
        return
    
    if not status_data.get('is_halted'):
        print_info("Circuit breaker is not currently triggered.")
        return
    
    print(f"Current status: 🚨 HALTED")
    print(f"Halt reason: {status_data.get('halt_reason', 'Unknown')}")
    print()
    
    # Confirm
    if not click.confirm("⚠️  Reset circuit breaker and resume trading?"):
        print("Cancelled.")
        return
    
    data = api_request(
        "POST",
        "/api/safety/circuit-breaker/reset",
        json_data={"confirm": True, "reset_by": "cli"}
    )
    
    if data:
        status = data.get('status', '')
        if status == 'reset':
            print_success("✅ Circuit breaker reset successfully")
            print(f"Reset by: {data.get('reset_by', 'cli')}")
        else:
            print_warning(f"⚠️  Status: {status}")
            print(data.get('message', ''))


@safety.command(name='heat')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']), default='table', help='Output format')
def portfolio_heat(output_format):
    """View portfolio heat (risk exposure)."""
    data = api_request("GET", "/api/safety/portfolio-heat")
    
    if not data:
        return
    
    if output_format == 'json':
        print(json.dumps(data, indent=2))
        return
    
    print()
    print("🔥 PORTFOLIO HEAT")
    print("═" * 50)
    print()
    
    current_heat = data.get('current_heat', 0)
    max_heat = data.get('max_heat', 0.10)
    
    heat_pct = (current_heat / max_heat * 100) if max_heat else 0
    
    # Visual bar
    bar_length = 30
    filled = int(bar_length * min(heat_pct / 100, 1))
    bar = "█" * filled + "░" * (bar_length - filled)
    
    heat_status = "🔴 HIGH" if current_heat >= max_heat * 0.8 else "🟢 OK"
    
    print(f"  Heat Level:  {heat_status}")
    print(f"  Current:     {format_percentage(current_heat)} / {format_percentage(max_heat)} max")
    print()
    print(f"  [{bar}] {heat_pct:.1f}%")
    print()
    
    if 'risk_amount' in data:
        print(f"  Risk Amount: {format_currency(data['risk_amount'])}")
    if 'portfolio_value' in data:
        print(f"  Portfolio:   {format_currency(data['portfolio_value'])}")


@safety.command()
@click.option('--symbol', '-s', required=True, help='Stock symbol')
@click.option('--price', '-p', type=float, required=True, help='Proposed entry price')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']), default='table', help='Output format')
def position_size(symbol, price, output_format):
    """Get volatility-based position sizing for a symbol."""
    data = api_request(
        "GET",
        f"/api/safety/position-sizing/{symbol.upper()}",
        params={"entry_price": price}
    )
    
    if not data:
        return
    
    if output_format == 'json':
        print(json.dumps(data, indent=2))
        return
    
    print()
    print(f"📐 Position Sizing: {symbol.upper()}")
    print("═" * 50)
    print()
    print(f"  Entry Price:      {format_currency(price)}")
    print(f"  ATR (volatility): {format_currency(data.get('atr', 0))}")
    print()
    print(f"  Recommended:")
    print(f"    Max Position:   {format_currency(data.get('max_position_value', 0))}")
    print(f"    Max Shares:     {data.get('max_shares', 0)}")
    print(f"    Risk per Share: {format_currency(data.get('risk_per_share', 0))}")


@safety.command(name='events')
@click.option('--limit', '-n', default=20, help='Number of events to show')
@click.option('--type', 'event_type', help='Filter by event type')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']), default='table', help='Output format')
def list_events(limit, event_type, output_format):
    """View risk events history."""
    params = {"limit": limit}
    if event_type:
        params["event_type"] = event_type
    
    data = api_request("GET", "/api/safety/events", params=params)
    
    if not data:
        return
    
    events = data.get('events', [])
    
    if not events:
        print_info("📭 No risk events found")
        return
    
    if output_format == 'json':
        print(json.dumps(data, indent=2))
        return
    
    rows = []
    for event in events:
        rows.append([
            event.get('id', ''),
            event.get('timestamp', '')[:16],
            event.get('event_type', ''),
            event.get('symbol', '') or '-',
            event.get('reason', '')[:30] + "..." if len(event.get('reason', '')) > 30 else event.get('reason', '')
        ])
    
    headers = ["ID", "Time", "Type", "Symbol", "Reason"]
    
    print()
    print("🚨 Risk Events")
    print("=" * 80)
    print(format_table(rows, headers))


@safety.command(name='circuit-history')
@click.option('--limit', '-n', default=20, help='Number of events to show')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']), default='table', help='Output format')
def circuit_history(limit, output_format):
    """View circuit breaker trigger history."""
    data = api_request("GET", "/api/safety/circuit-breaker/history", params={"limit": limit})
    
    if not data:
        return
    
    events = data.get('events', [])
    
    if not events:
        print_info("📭 No circuit breaker events found")
        return
    
    if output_format == 'json':
        print(json.dumps(data, indent=2))
        return
    
    rows = []
    for event in events:
        triggered = event.get('triggered_at', '')[:16]
        reset = event.get('reset_at', '')
        reset_str = reset[:16] if reset else "Not reset"
        
        rows.append([
            event.get('id', ''),
            triggered,
            reset_str,
            event.get('reset_by', '-') or '-',
            format_currency(event.get('portfolio_value', 0)) if event.get('portfolio_value') else '-',
            format_percentage(event.get('daily_pnl', 0)) if event.get('daily_pnl') else '-',
            event.get('reason', '')[:30] + "..." if len(event.get('reason', '')) > 30 else event.get('reason', '')
        ])
    
    headers = ["ID", "Triggered", "Reset", "Reset By", "Portfolio", "Daily P&L", "Reason"]
    
    print()
    print("⚡ Circuit Breaker History")
    print("=" * 100)
    print(format_table(rows, headers))


@safety.command()
def limits():
    """View current risk limits."""
    data = api_request("GET", "/api/safety/status")
    
    if not data:
        return
    
    risk_limits = data.get('risk_limits', {})
    
    print()
    print("📊 RISK LIMITS")
    print("═" * 50)
    print()
    
    if risk_limits:
        for key, value in risk_limits.items():
            print(f"  {key.replace('_', ' ').title():<25}: {value}")
    else:
        print_info("Risk limits configured in settings.yaml")
        print()
        print("Default limits:")
        print("  Max Position Size:        10% of portfolio")
        print("  Max Portfolio Heat:       10%")
        print("  Max Open Positions:       5")
        print("  Daily Loss Limit:         -3%")
        print("  Max Drawdown:             -15%")
        print("  Max Consecutive Losses:   5")
