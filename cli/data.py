"""Data management commands."""
import click
import json

from cli.utils import (
    api_request, print_success, print_error, print_info, print_warning,
    format_table
)


@click.group()
def data():
    """Data ingestion and management commands."""
    pass


@data.command()
@click.option('--symbols', '-s', required=True, help='Comma-separated stock symbols')
@click.option('--period', '-p', default='1y', help='Data period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)')
def ingest(symbols, period):
    """
    Ingest data for stock symbols.
    
    Examples:
        trademind data ingest --symbols AAPL,MSFT,TSLA
        trademind data ingest -s AAPL -p 2y
    """
    symbol_list = [s.strip().upper() for s in symbols.split(',')]
    
    print()
    print("📥 DATA INGESTION")
    print("═" * 50)
    print()
    print(f"Symbols: {', '.join(symbol_list)}")
    print(f"Period:  {period}")
    print()
    
    # Note: In a full implementation, there would be a data ingestion API endpoint
    # For now, we'll use the analyze endpoint which triggers data fetch
    
    for symbol in symbol_list:
        print_info(f"Fetching data for {symbol}...")
        
        # This triggers data ingestion via the agent analyze endpoint
        result = api_request("POST", f"/api/agent/analyze/{symbol}")
        
        if result:
            print_success(f"  ✅ {symbol} - Data ingested")
        else:
            print_error(f"  ❌ {symbol} - Failed to ingest")
    
    print()
    print_success("Ingestion complete!")


@data.command()
def status():
    """Check data status for watchlist symbols."""
    print()
    print("📊 DATA STATUS")
    print("═" * 50)
    print()
    
    # Get default watchlist from settings
    # This would ideally have a dedicated endpoint
    print_info("Data status check requires agent orchestrator integration")
    print()
    print("Symbols with data will show in portfolio and trades.")
    print("Use 'trademind data ingest' to fetch data for new symbols.")


@data.command()
@click.argument('symbol')
@click.option('--days', '-d', default=30, help='Number of days to show')
def show(symbol, days):
    """View data for a symbol."""
    print()
    print(f"📈 DATA: {symbol.upper()}")
    print("═" * 50)
    print()
    
    # Try to get signal which includes price data
    result = api_request(
        "POST", 
        "/api/strategies/signal",
        params={"symbol": symbol.upper(), "strategy": "rsi"}
    )
    
    if result:
        print(f"Current Price: ${result.get('price', 0):.2f}")
        print()
        print_info("Full historical data view requires dedicated endpoint")
    else:
        print_error(f"No data available for {symbol.upper()}")
        print_info(f"Run: trademind data ingest --symbols {symbol.upper()}")


@data.command()
def update_indicators():
    """Update technical indicators for all stored data."""
    print_info("Indicator update requires data management endpoint")
    print()
    print("Indicators are calculated automatically when data is fetched.")


@data.command()
def clear_cache():
    """Clear data cache."""
    if click.confirm("⚠️  Clear all cached data?"):
        print_info("Data cache clearing requires data management endpoint")
    else:
        print("Cancelled.")


@data.command()
def verify():
    """Verify data quality."""
    print()
    print("🔍 DATA QUALITY VERIFICATION")
    print("═" * 50)
    print()
    
    print_info("Data verification requires data management endpoint")
    print()
    print("Checks would include:")
    print("  - Missing data points")
    print("  - Price anomalies")
    print("  - Stale data detection")
    print("  - Data completeness")
