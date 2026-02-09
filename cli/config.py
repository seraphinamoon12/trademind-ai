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
            
            # Sentiment
            click.echo("\n🎭 SENTIMENT ANALYSIS:")
            click.echo(f"  Source:               {cfg.get('sentiment_source', 'auto')}")
            click.echo(f"  Enabled:              {cfg.get('sentiment_enabled', True)}")
            click.echo(f"  Cache TTL:            {cfg.get('sentiment_cache_ttl', 1800)}s")
            
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

# Sentiment configuration commands
@config.group()
def sentiment():
    """Sentiment analysis configuration commands."""
    pass

def _set_sentiment_source(source):
    """Internal function to set sentiment source."""
    try:
        response = requests.post(
            f"{API_BASE}/api/config",
            json={"key": "sentiment_source", "value": source}
        )
        if response.status_code == 200:
            if source == 'llm':
                print_success("✓ Sentiment source set to 'llm' (AI-powered analysis)")
                click.echo("  Note: Requires ZAI_API_KEY to be configured")
            elif source == 'technical':
                print_success("✓ Sentiment source set to 'technical' (RSI + volume)")
                click.echo("  Benefits: No API costs, faster, works offline")
            else:
                print_success("✓ Sentiment source set to 'auto' (smart fallback)")
            return True
        else:
            print_error(f"Failed to set sentiment source: {response.text}")
            return False
    except Exception as e:
        print_error(f"Error: {e}")
        return False

@sentiment.command()
def show():
    """Show current sentiment configuration."""
    try:
        response = requests.get(f"{API_BASE}/api/config")
        if response.status_code == 200:
            cfg = response.json()
            click.echo("\n" + "=" * 50)
            click.echo("🎭 SENTIMENT ANALYSIS CONFIGURATION")
            click.echo("=" * 50)
            
            source = cfg.get('sentiment_source', 'auto')
            click.echo(f"\n  Source:               {source}")
            
            if source == 'llm':
                click.echo("  Mode:                 AI-powered (ZAI GLM-4.7)")
                click.echo(f"  Model:                {cfg.get('zai_model', 'N/A')}")
                click.echo(f"  Temperature:          {cfg.get('zai_temperature', 0.3)}")
            elif source == 'technical':
                click.echo("  Mode:                 Technical indicators")
                click.echo(f"  Confidence Threshold: {cfg.get('sentiment_confidence_threshold', 0.7)}")
            else:
                click.echo("  Mode:                 Auto (LLM if available, else technical)")
                has_key = bool(cfg.get('zai_api_key'))
                click.echo(f"  API Key Available:    {has_key}")
                click.echo(f"  Will Use:             {'LLM' if has_key else 'Technical'}")
            
            click.echo(f"  Cache TTL:            {cfg.get('sentiment_cache_ttl', 1800)} seconds")
            click.echo(f"  Agent Weight:         {cfg.get('sentiment_weight', 0.30) * 100:.0f}%")
            click.echo("\n" + "=" * 50)
        else:
            print_error(f"Failed to get config: {response.status_code}")
    except Exception as e:
        print_error(f"Error: {e}")

@sentiment.command()
@click.argument('source', type=click.Choice(['llm', 'technical', 'auto']))
def set_source(source):
    """Set sentiment analysis source.
    
    SOURCE options:
      llm        - Use ZAI GLM-4.7 AI model (requires API key)
      technical  - Use RSI, volume, momentum indicators
      auto       - Use LLM if available, else technical (default)
    """
    _set_sentiment_source(source)

@sentiment.command()
def use_llm():
    """Quick command to use LLM sentiment."""
    _set_sentiment_source('llm')

@sentiment.command()
def use_technical():
    """Quick command to use technical sentiment."""
    _set_sentiment_source('technical')

@sentiment.command()
def use_auto():
    """Quick command to use auto sentiment mode."""
    _set_sentiment_source('auto')
