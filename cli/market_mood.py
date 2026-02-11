"""Market Mood CLI commands."""
import click
import json
from datetime import datetime, timedelta

from cli.utils import (
    api_request, print_success, print_error, print_info, print_warning,
    format_table, format_currency, format_percentage, print_panel
)


@click.group()
def market_mood():
    """Market Mood Detection commands."""
    pass


@market_mood.command(name='status')
def get_status():
    """
    Get current market mood status.
    
    Examples:
        trademind market-mood status
    """
    print()
    print("🧠 MARKET MOOD STATUS")
    print("═" * 50)
    print()
    
    print_info("Fetching current market mood...")
    
    data = api_request("GET", "/api/market/mood")
    
    if not data:
        return
    
    print_success("✅ STATUS RETRIEVED")
    print()
    
    mood = data.get('mood', {})
    composite_score = mood.get('composite_score', 0.0)
    confidence = mood.get('confidence', 0.0)
    trend = mood.get('trend', 'stable')
    
    sentiment_map = {
        'extreme_fear': '😱 Extreme Fear',
        'fear': '😰 Fear',
        'neutral': '😐 Neutral',
        'greed': '😊 Greed',
        'extreme_greed': '🤑 Extreme Greed',
    }
    
    print(f"  Sentiment:       {sentiment_map.get('neutral', 'Neutral')}")
    print(f"  Score:           {composite_score:.1f}")
    print(f"  Trend:           {trend}")
    print(f"  Confidence:      {confidence:.1%}")
    print()
    
    indicators = mood.get('indicator_details', {})
    if indicators:
        print("  📊 INDICATORS:")
        for name, details in indicators.items():
            score = details.get('score', 'N/A')
            indicator_trend = details.get('trend', 'N/A')
            print(f"    {name}: {score} ({indicator_trend})")
        print()


@market_mood.command(name='history')
@click.option('--days', '-d', default=7, help='Number of days of history')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']), default='table', help='Output format')
def get_history(days, output_format):
    """
    Get historical mood data.
    
    Examples:
        trademind market-mood history
        trademind market-mood history --days 30
    """
    print()
    print("📈 MARKET MOOD HISTORY")
    print("═" * 50)
    print()
    
    data = api_request("GET", f"/api/market/mood/history?days={days}")
    
    if not data:
        return
    
    history = data.get('history', [])
    
    if output_format == 'json':
        print(json.dumps(history, indent=2))
        return
    
    if not history:
        print_warning("No history data available")
        return
    
    print_success(f"✅ {len(history)} DAYS OF HISTORY")
    print()
    
    rows = []
    for entry in history[-10:]:  # Show last 10
        timestamp = entry.get('timestamp', '')
        if isinstance(timestamp, str):
            date_str = timestamp[:10]
        else:
            date_str = str(timestamp)[:10]
        
        score = entry.get('overall_score', 0.0)
        sentiment = entry.get('sentiment', 'neutral')
        confidence = entry.get('confidence', 0.0)
        
        rows.append([date_str, f"{score:.1f}", sentiment, f"{confidence:.1%}"])
    
    headers = ["Date", "Score", "Sentiment", "Confidence"]
    print(format_table(rows, headers))
    
    if len(history) > 10:
        print()
        print_info(f"Showing last 10 of {len(history)} entries")


@market_mood.command(name='signals')
def get_signals():
    """
    Get current trading signals based on market mood.
    
    Examples:
        trademind market-mood signals
    """
    print()
    print("🎯 TRADING SIGNALS")
    print("═" * 50)
    print()
    
    print_info("Fetching trading signals...")
    
    data = api_request("GET", "/api/market/mood/signals")
    
    if not data:
        return
    
    print_success("✅ SIGNALS RETRIEVED")
    print()
    
    signals = data.get('signals', {})
    signal = signals.get('signal', 'NO_SIGNAL')
    mood_classification = signals.get('mood_classification', 'neutral')
    confidence = signals.get('confidence', 0.0)
    score = signals.get('score', 0.0)
    recommendations = signals.get('recommendations', [])
    
    signal_colors = {
        'STRONG_BUY': 'green',
        'BUY': 'blue',
        'HOLD': 'yellow',
        'REDUCE': 'orange',
        'SELL': 'red',
        'NO_SIGNAL': 'gray',
    }
    
    color = signal_colors.get(signal, 'white')
    print(f"  Signal:          {signal}")
    print(f"  Mood:            {mood_classification}")
    print(f"  Score:           {score:.1f}")
    print(f"  Confidence:      {confidence:.1%}")
    print()
    
    if recommendations:
        print("  💡 RECOMMENDATIONS:")
        for rec in recommendations:
            print(f"    • {rec}")
        print()


@market_mood.command(name='refresh')
def refresh_mood():
    """
    Force refresh of all market mood indicators.
    
    Examples:
        trademind market-mood refresh
    """
    print()
    print("🔄 REFRESHING INDICATORS")
    print("═" * 50)
    print()
    
    print_info("Refreshing market mood indicators...")
    
    data = api_request("POST", "/api/market/mood/refresh")
    
    if not data:
        return
    
    print_success("✅ INDICATORS REFRESHED")
    print()
    
    mood = data.get('mood', {})
    composite_score = mood.get('composite_score', 0.0)
    
    print(f"  Current Mood Score: {composite_score:.1f}")
    print()


@market_mood.command(name='backtest')
@click.option('--start-date', '-s', required=True, help='Start date (YYYY-MM-DD)')
@click.option('--end-date', '-e', required=True, help='End date (YYYY-MM-DD)')
@click.option('--symbol', '-S', default='SPY', help='Symbol to backtest (default: SPY)')
@click.option('--initial-capital', '-c', default=100000, help='Initial capital (default: 100000)')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']), default='table', help='Output format')
@click.option('--export', is_flag=True, help='Export results to files')
def run_backtest(start_date, end_date, symbol, initial_capital, output_format, export):
    """
    Run a mood-based backtest.
    
    Examples:
        trademind market-mood backtest --start-date 2023-01-01 --end-date 2023-12-31
        trademind market-mood backtest -s 2023-01-01 -e 2023-12-31 --symbol QQQ --capital 50000
        trademind market-mood backtest -s 2023-01-01 -e 2023-12-31 --export
    """
    print()
    print("🧪 RUNNING MOOD-BASED BACKTEST")
    print("═" * 60)
    print()
    print(f"  Symbol:         {symbol.upper()}")
    print(f"  Start Date:     {start_date}")
    print(f"  End Date:       {end_date}")
    print(f"  Initial Capital: {format_currency(initial_capital)}")
    print()
    
    print_info("Fetching data and running backtest...")
    print()
    
    if export:
        data = api_request(
            "POST",
            f"/api/market/mood/backtest/export?start_date={start_date}&end_date={end_date}&symbol={symbol}&initial_capital={initial_capital}"
        )
    else:
        data = api_request(
            "POST",
            f"/api/market/mood/backtest?start_date={start_date}&end_date={end_date}&symbol={symbol}&initial_capital={initial_capital}"
        )
    
    if not data:
        return
    
    if output_format == 'json':
        print(json.dumps(data, indent=2))
        return
    
    print_success("✅ BACKTEST COMPLETE")
    print()
    
    if export:
        files = data.get('files', {})
        print("  📁 EXPORTED FILES:")
        for file_type, file_path in files.items():
            print(f"    {file_type}: {file_path}")
        print()
        trades_count = data.get('trades_count', 0)
        print(f"  Total Trades: {trades_count}")
        return
    
    summary = data.get('backtest_summary', {})
    metrics = data.get('performance_metrics', {})
    buy_and_hold = data.get('buy_and_hold', {})
    
    final_capital = summary.get('final_capital', initial_capital)
    total_trades = summary.get('total_trades', 0)
    
    total_return_pct = metrics.get('total_return_pct', 0)
    annualized_return = metrics.get('annualized_return', 0)
    win_rate = metrics.get('win_rate', 0)
    max_drawdown = metrics.get('max_drawdown', 0)
    sharpe_ratio = metrics.get('sharpe_ratio', 0)
    sortino_ratio = metrics.get('sortino_ratio', 0)
    calmar_ratio = metrics.get('calmar_ratio', 0)
    volatility = metrics.get('volatility', 0)
    
    print(f"  Final Capital:   {format_currency(final_capital)}")
    print(f"  Total Return:    {format_percentage(total_return_pct)}")
    print(f"  Annualized:      {format_percentage(annualized_return)}")
    print()
    
    print(f"  Total Trades:    {total_trades}")
    print(f"  Win Rate:        {format_percentage(win_rate)}")
    print(f"  Avg Return:      {format_currency(metrics.get('avg_return', 0))}")
    print()
    
    print(f"  Max Drawdown:    {format_percentage(max_drawdown)}")
    print(f"  Sharpe Ratio:    {sharpe_ratio:.2f}")
    print(f"  Sortino Ratio:   {sortino_ratio:.2f}")
    print(f"  Calmar Ratio:    {calmar_ratio:.2f}")
    print(f"  Volatility:      {format_percentage(volatility)}")
    print()
    
    buy_and_hold_return = buy_and_hold.get('return_pct', 0)
    print(f"  Buy & Hold:      {format_percentage(buy_and_hold_return)}")
    
    if total_return_pct > buy_and_hold_return:
        print(f"  🎯 Beat Market:   {format_percentage(total_return_pct - buy_and_hold_return)}")
    else:
        print(f"  ⚠️  Underperformed: {format_percentage(buy_and_hold_return - total_return_pct)}")
    print()
    
    signals_by_mood = data.get('signals_by_mood', {})
    if signals_by_mood:
        print("  📊 SIGNALS BY MOOD:")
        by_mood = signals_by_mood.get('by_mood_classification', {})
        for mood, count in by_mood.items():
            print(f"    {mood}: {count}")
        print()
    
    trades_by_mood = data.get('trades_by_mood', {})
    if trades_by_mood:
        print("  📈 TRADES BY MOOD:")
        for mood, trade_data in trades_by_mood.items():
            count = trade_data.get('count', 0)
            avg_pnl = trade_data.get('avg_pnl', 0)
            win_rate_mood = trade_data.get('win_rate', 0)
            print(f"    {mood}: {count} trades, avg: {format_currency(avg_pnl)}, win: {format_percentage(win_rate_mood)}")
        print()


@market_mood.command(name='dashboard')
def get_dashboard():
    """
    Get comprehensive market mood dashboard.
    
    Examples:
        trademind market-mood dashboard
    """
    print()
    print("📊 MARKET MOOD DASHBOARD")
    print("═" * 50)
    print()
    
    print_info("Fetching dashboard data...")
    
    data = api_request("GET", "/api/market/mood/dashboard")
    
    if not data:
        return
    
    print_success("✅ DASHBOARD RETRIEVED")
    print()
    
    dashboard = data.get('dashboard', {})
    mood = dashboard.get('mood', {})
    signals = dashboard.get('signals', {})
    trend = dashboard.get('trend', {})
    
    print("  🧠 CURRENT MOOD:")
    print(f"    Score:     {mood.get('composite_score', 0.0):.1f}")
    print(f"    Trend:     {mood.get('trend', 'stable')}")
    print(f"    Confidence: {mood.get('confidence', 0.0):.1%}")
    print()
    
    print("  🎯 SIGNALS:")
    print(f"    Signal:    {signals.get('signal', 'NO_SIGNAL')}")
    print(f"    Mood:      {signals.get('mood_classification', 'neutral')}")
    print(f"    Strength:  {signals.get('strength', 'N/A')}")
    print()
    
    if trend:
        print("  📈 TREND:")
        print(f"    Direction: {trend.get('direction', 'N/A')}")
        print(f"    Strength:  {trend.get('strength', 'N/A')}")
        print(f"    Duration:  {trend.get('duration_days', 0)} days")
        print()
    
    position_sizing = dashboard.get('position_sizing', {})
    if position_sizing:
        print("  📏 POSITION SIZING:")
        print(f"    Multiplier: {position_sizing.get('multiplier', 1.0):.2f}x")
        print(f"    Max Pos:    {format_percentage(position_sizing.get('max_position_pct', 0.1))}")
        print()


@market_mood.command(name='alerts')
def get_alerts():
    """
    Get active market mood alerts.
    
    Examples:
        trademind market-mood alerts
    """
    print()
    print("🚨 MARKET MOOD ALERTS")
    print("═" * 50)
    print()
    
    print_info("Checking for alerts...")
    
    data = api_request("GET", "/api/market/mood/alerts")
    
    if not data:
        return
    
    alerts = data.get('alerts', [])
    count = data.get('count', 0)
    
    if count == 0:
        print_success("✅ No active alerts")
        print()
        return
    
    print_warning(f"⚠️  {count} ACTIVE ALERT(S)")
    print()
    
    for alert in alerts:
        severity = alert.get('severity', 'info')
        alert_type = alert.get('type', 'general')
        message = alert.get('message', '')
        recommendation = alert.get('recommendation', '')
        
        severity_icon = {
            'info': 'ℹ️',
            'warning': '⚠️',
            'error': '❌',
        }
        
        print(f"  {severity_icon.get(severity, '•')} [{alert_type.upper()}] {message}")
        if recommendation:
            print(f"    → {recommendation}")
        print()
