"""TradeMind AI CLI - Main entry point."""
import click
from cli.utils import print_panel

# Import command groups
from cli.server import server
from cli.portfolio import portfolio
from cli.trades import trades
from cli.strategies import strategies
from cli.safety import safety
from cli.backtest import backtest
from cli.data import data
from cli.config import config


@click.group()
@click.version_option(version="1.0.0", prog_name="trademind")
@click.pass_context
def cli(ctx):
    """
    🧠 TradeMind AI - Command Line Interface
    
    Manage your AI-powered trading agent from the command line.
    
    Examples:
        trademind server status      # Check server status
        trademind portfolio          # View portfolio summary
        trademind trades list        # List recent trades
        trademind safety status      # Check safety systems
    
    Environment Variables:
        TRADEMIND_API_URL    API endpoint URL (default: http://localhost:8000)
    """
    # Ensure context object exists
    ctx.ensure_object(dict)


# Register command groups
cli.add_command(server)
cli.add_command(portfolio)
cli.add_command(trades)
cli.add_command(strategies)
cli.add_command(safety)
cli.add_command(backtest)
cli.add_command(data)
cli.add_command(config)


@cli.command()
def examples():
    """Show usage examples."""
    examples_text = """
[bold cyan]Server Management[/bold cyan]
  trademind server start           # Start the trading server
  trademind server stop            # Stop the trading server
  trademind server status          # Check if server is running

[bold cyan]Portfolio Commands[/bold cyan]
  trademind portfolio              # View portfolio summary
  trademind portfolio holdings     # Show detailed holdings
  trademind portfolio performance  # View performance metrics

[bold cyan]Trade Commands[/bold cyan]
  trademind trades list            # List recent trades (default: 50)
  trademind trades list --limit 10 # List last 10 trades
  trademind trades list --symbol AAPL  # Filter by symbol

[bold cyan]Strategy Commands[/bold cyan]
  trademind strategies list        # List all strategies
  trademind strategies enable rsi  # Enable RSI strategy
  trademind strategies disable ma  # Disable MA strategy

[bold cyan]Safety Commands[/bold cyan]
  trademind safety status          # View safety system status
  trademind safety circuit-breaker # Check circuit breaker
  trademind safety emergency-stop --reason "Manual halt"  # EMERGENCY STOP

[bold cyan]Backtest Commands[/bold cyan]
  trademind backtest run --symbol AAPL --strategy rsi --days 180
  trademind backtest list          # List recent backtests

[bold cyan]Data Commands[/bold cyan]
  trademind data ingest --symbols AAPL,MSFT,TSLA  # Ingest stock data
  trademind data status            # Check data status

[bold cyan]Config Commands[/bold cyan]
  trademind config show            # Show all configuration
  trademind config get trading.max_position_pct   # Get specific value
    """
    
    try:
        from rich.console import Console
        console = Console()
        console.print(examples_text)
    except ImportError:
        # Fallback without rich formatting
        print("\nServer Management")
        print("  trademind server start")
        print("  trademind server status")
        print("\nPortfolio Commands")
        print("  trademind portfolio")
        print("  trademind portfolio holdings")
        print("\nTrade Commands")
        print("  trademind trades list")
        print("  trademind trades list --limit 10 --symbol AAPL")
        print("\nStrategy Commands")
        print("  trademind strategies list")
        print("  trademind strategies enable/disable <name>")
        print("\nSafety Commands")
        print("  trademind safety status")
        print("  trademind safety emergency-stop")
        print("\nBacktest Commands")
        print("  trademind backtest run --symbol AAPL --strategy rsi --days 180")
        print("\nData Commands")
        print("  trademind data ingest --symbols AAPL,MSFT,TSLA")
        print("\nConfig Commands")
        print("  trademind config show")
        print("  trademind config get <key>")


if __name__ == "__main__":
    cli()
