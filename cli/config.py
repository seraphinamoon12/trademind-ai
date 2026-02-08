"""Configuration commands for CLI."""
import click
import requests
from cli.utils import API_BASE, print_error, print_success, format_value

@click.group()
def config():
    """Configuration management commands."""
    pass

@config.command()
def show():
    """Show all configuration settings."""
    try:
        response = requests.get(f"{API_BASE}/api/config")
        if response.status_code == 200:
            cfg = response.json()
            click.echo("\n" + "=" * 50)
            click.echo("⚙️  TRADEMIND CONFIGURATION")
            click.echo("=" * 50)
            
            # Trading Settings
            click.echo("\n📊 TRADING:")
            click.echo(f"  Starting Capital:     ${cfg.get('starting_capital', 'N/A'):,.2f}")
            click.echo(f"  Max Position:         {cfg.get('max_position_pct', 0)*100:.1f}%")
            click.echo(f"  Check Interval:       {cfg.get('check_interval_minutes', 0)} min")
            click.echo(f"  Trading Hours:        {cfg.get('trading_start', 'N/A')} - {cfg.get('trading_end', 'N/A')}")
            
            # Circuit Breakers
            click.echo("\n🛡️  CIRCUIT BREAKERS:")
            click.echo(f"  Daily Loss Limit:     {cfg.get('circuit_breaker_daily_loss_pct', 0)*100:.1f}%")
            click.echo(f"  Warning Drawdown:     {cfg.get('circuit_breaker_warning_drawdown_pct', 0)*100:.1f}%")
            click.echo(f"  Max Drawdown:         {cfg.get('circuit_breaker_max_drawdown_pct', 0)*100:.1f}%")
            click.echo(f"  Consecutive Losses:   {cfg.get('circuit_breaker_consecutive_loss_limit', 0)}")
            click.echo(f"  Auto Liquidate:       {cfg.get('circuit_breaker_auto_liquidate', False)}")
            
            # Position Limits
            click.echo("\n📈 POSITION LIMITS:")
            click.echo(f"  Max Open Positions:   {cfg.get('max_open_positions', 0)}")
            click.echo(f"  Max Portfolio Heat:   {cfg.get('max_portfolio_heat_pct', 0)*100:.1f}%")
            click.echo(f"  No Trades After:      {cfg.get('no_new_trades_after', 'N/A')}")
            
            # Liquidity Filters
            click.echo("\n💧 LIQUIDITY FILTERS:")
            click.echo(f"  Min Volume:           ${cfg.get('min_avg_daily_volume', 0):,}")
            click.echo(f"  Min Price:            ${cfg.get('min_price', 0):.2f}")
            click.echo(f"  Max Spread:           {cfg.get('max_spread_pct', 0)*100:.2f}%")
            click.echo(f"  Min Market Cap:       ${cfg.get('min_market_cap', 0):,}")
            
            # Transaction Costs
            click.echo("\n💰 TRANSACTION COSTS:")
            click.echo(f"  Commission/Share:     ${cfg.get('commission_per_share', 0):.3f}")
            click.echo(f"  Min Commission:       ${cfg.get('min_commission', 0):.2f}")
            click.echo(f"  Slippage:             {cfg.get('slippage_pct', 0)*100:.2f}%")
            click.echo(f"  Spread:               {cfg.get('spread_pct', 0)*100:.3f}%")
            
            # Strategy Settings
            click.echo("\n🎯 STRATEGY:")
            click.echo(f"  Min Win Rate:         {cfg.get('strategy_min_win_rate', 0)*100:.1f}%")
            click.echo(f"  Min Profit Factor:    {cfg.get('strategy_min_profit_factor', 0):.2f}")
            click.echo(f"  Auto Disable:         {cfg.get('strategy_auto_disable', False)}")
            
            # Sector Limits
            click.echo("\n🏭 SECTOR LIMITS:")
            click.echo(f"  Max Per Sector:       {cfg.get('max_sector_allocation_pct', 0)*100:.1f}%")
            
            click.echo("\n" + "=" * 50)
        else:
            print_error(f"Failed to get config: {response.status_code}")
    except Exception as e:
        print_error(f"Error: {e}")

@config.command()
@click.argument('key')
def get(key):
    """Get a specific config value."""
    try:
        response = requests.get(f"{API_BASE}/api/config/{key}")
        if response.status_code == 200:
            value = response.json().get('value')
            click.echo(f"{key} = {format_value(value)}")
        else:
            print_error(f"Config key not found: {key}")
    except Exception as e:
        print_error(f"Error: {e}")

@config.command()
@click.argument('key')
@click.argument('value')
def set(key, value):
    """Set a config value."""
    try:
        # Try to parse value as number/bool
        parsed_value = value
        if value.lower() in ('true', 'false'):
            parsed_value = value.lower() == 'true'
        else:
            try:
                if '.' in value:
                    parsed_value = float(value)
                else:
                    parsed_value = int(value)
            except ValueError:
                pass  # Keep as string
        
        response = requests.post(
            f"{API_BASE}/api/config",
            json={"key": key, "value": parsed_value}
        )
        if response.status_code == 200:
            print_success(f"Set {key} = {format_value(parsed_value)}")
        else:
            print_error(f"Failed to set config: {response.text}")
    except Exception as e:
        print_error(f"Error: {e}")

@config.command()
@click.confirmation_option(prompt='Are you sure you want to reset all config to defaults?')
def reset():
    """Reset configuration to defaults."""
    try:
        response = requests.post(f"{API_BASE}/api/config/reset")
        if response.status_code == 200:
            print_success("Configuration reset to defaults")
        else:
            print_error("Failed to reset config")
    except Exception as e:
        print_error(f"Error: {e}")

@config.command()
def validate():
    """Validate current configuration."""
    try:
        response = requests.get(f"{API_BASE}/api/config/validate")
        if response.status_code == 200:
            result = response.json()
            if result.get('valid'):
                print_success("✓ Configuration is valid")
            else:
                print_error("✗ Configuration has errors:")
                for error in result.get('errors', []):
                    click.echo(f"  - {error}")
        else:
            print_error("Failed to validate config")
    except Exception as e:
        print_error(f"Error: {e}")

@config.command()
@click.option('--output', '-o', type=click.File('w'), help='Output file')
def export(output):
    """Export configuration to YAML."""
    try:
        response = requests.get(f"{API_BASE}/api/config/export")
        if response.status_code == 200:
            yaml_content = response.json().get('yaml')
            if output:
                output.write(yaml_content)
                print_success(f"Config exported to {output.name}")
            else:
                click.echo(yaml_content)
        else:
            print_error("Failed to export config")
    except Exception as e:
        print_error(f"Error: {e}")

@config.command()
@click.argument('file', type=click.File('r'))
def import_config(file):
    """Import configuration from YAML file."""
    try:
        yaml_content = file.read()
        response = requests.post(
            f"{API_BASE}/api/config/import",
            json={"yaml": yaml_content}
        )
        if response.status_code == 200:
            print_success("Configuration imported successfully")
        else:
            print_error(f"Failed to import: {response.text}")
    except Exception as e:
        print_error(f"Error: {e}")

# Convenience commands for common config changes
@config.group()
def safety():
    """Quick safety configuration commands."""
    pass

@safety.command()
@click.argument('pct', type=float)
def daily_loss(pct):
    """Set daily loss limit percentage."""
    set.callback('circuit_breaker_daily_loss_pct', str(pct / 100))

@safety.command()
@click.argument('pct', type=float)
def max_drawdown(pct):
    """Set max drawdown percentage."""
    set.callback('circuit_breaker_max_drawdown_pct', str(pct / 100))

@safety.command()
@click.argument('count', type=int)
def max_positions(count):
    """Set max open positions."""
    set.callback('max_open_positions', str(count))

@safety.command()
@click.argument('minutes', type=int)
def check_interval(minutes):
    """Set check interval in minutes."""
    set.callback('check_interval_minutes', str(minutes))
