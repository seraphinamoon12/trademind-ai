#!/usr/bin/env python3
"""
LangGraph Auto-Trader

Runs LangGraph multi-agent workflow continuously on watchlist symbols.
Auto-approves trades with high confidence.
Now with position awareness and exit strategy monitoring.
"""

import asyncio
import sys
import time
import signal
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

sys.path.insert(0, '.')

from src.trading_graph.graph import create_trading_graph
from src.trading_graph.state import TradingState
from src.position_manager import PositionManager
from src.config import settings

logger = logging.getLogger(__name__)

# Check if using recommended ib_insync broker
if hasattr(settings, 'ibkr_use_insync') and not settings.ibkr_use_insync:
    logger.warning("Auto-trader works best with ib_insync broker (ibkr_use_insync=True). "
                   "Consider enabling it for better performance and stability.")

# Watchlist - updated with diversification recommendations
WATCHLIST = [
    # Technology (4)
    "AAPL", "MSFT", "NVDA", "AMD",
    # Communications (1)
    "GOOGL",
    # Healthcare (2)
    "JNJ", "XLV",
    # Financials (2)
    "JPM", "XLF",
    # Energy (2)
    "XOM", "XLE",
    # Consumer (2)
    "TSLA", "PG",
    # Industrials (1)
    "CAT",
    # Utilities (1)
    "NEE",
    # Materials (1)
    "AG",
    # Commodities (2)
    "IAU", "IBIT",
    # ETFs/Leverage (3)
    "TQQQ", "SPY", "QQQ"
]

# Auto-trading settings
MIN_CONFIDENCE = 0.65  # Minimum confidence to trade
CHECK_INTERVAL = 60    # Seconds between checks
MAX_POSITIONS = 10     # Max number of positions to hold

# Exit strategy settings (from config or defaults)
TAKE_PROFIT_PCT = settings.exit_take_profit_pct if hasattr(settings, 'exit_take_profit_pct') else 0.10
STOP_LOSS_PCT = settings.exit_stop_loss_pct if hasattr(settings, 'exit_stop_loss_pct') else 0.05
EXIT_CHECK_ENABLED = settings.exit_strategy_enabled if hasattr(settings, 'exit_strategy_enabled') else True

# Control flag
running = True

def signal_handler(sig, frame):
    global running
    print("\n⚠️  Shutting down LangGraph Auto-Trader...")
    running = False

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


async def analyze_symbol(
    graph,
    symbol: str,
    position_data: Dict[str, Any],
    portfolio_value: float,
    cash_balance: float,
    sector_exposure: Dict[str, float]
) -> Optional[dict]:
    """
    Run LangGraph analysis on a single symbol with position awareness.
    
    Args:
        graph: LangGraph trading graph
        symbol: Symbol to analyze
        position_data: Current positions dict
        portfolio_value: Total portfolio value
        cash_balance: Available cash
        sector_exposure: Current sector exposure percentages
        
    Returns:
        Analysis result dict or None if error
    """
    try:
        state = TradingState(
            symbol=symbol,
            timeframe="1d",
            positions=position_data,
            portfolio_value=portfolio_value,
            cash_balance=cash_balance,
            position_entry_prices={},
            sector_exposure=sector_exposure,
            market_data={},
            technical_indicators={},
            technical_signals={},
            sentiment_signals={},
            risk_signals={},
            debate_result={},
            final_decision={},
            final_action=None,
            confidence=0.0,
            executed_trade={},
            order_id=None,
            human_approved=True,  # Auto-approve for auto-trader
            human_feedback=None,
            messages=[],
            timestamp=datetime.now(timezone.utc).isoformat(),
            workflow_id=f"auto-trade-{symbol}-{int(time.time())}",
            iteration=0,
            current_node="start",
            error=None,
            retry_count=0
        )
        
        config = {
            "configurable": {
                "thread_id": f"auto-trade-{symbol}-{int(time.time())}"
            }
        }
        
        result = await graph.ainvoke(state, config=config)
        
        # Debug logging for API response (Medium Priority Fix #5)
        if result:
            print(f"   API Response: action={result.get('final_action')}, conf={result.get('confidence'):.1%}")
            if result.get('error'):
                print(f"   API Error: {result.get('error')}")
        
        return result
        
    except Exception as e:
        print(f"   ❌ Error analyzing {symbol}: {e}")
        return None


async def run_auto_trader():
    """Main auto-trading loop with position awareness."""
    global running
    
    print("="*70)
    print("🤖 LANGGRAPH AUTO-TRADER WITH POSITION AWARENESS")
    print("="*70)
    print()
    print("Configuration:")
    print(f"  Watchlist: {len(WATCHLIST)} symbols")
    print(f"  Min Confidence: {MIN_CONFIDENCE:.0%}")
    print(f"  Check Interval: {CHECK_INTERVAL}s")
    print(f"  Max Positions: {MAX_POSITIONS}")
    print(f"  Sector Limit: {settings.max_sector_allocation_pct:.0%}")
    print(f"  Take-Profit: {TAKE_PROFIT_PCT:.0%} | Stop-Loss: {STOP_LOSS_PCT:.0%}")
    print(f"  Exit Strategy: {'Enabled' if EXIT_CHECK_ENABLED else 'Disabled'}")
    print()
    print("Press Ctrl+C to stop")
    print("="*70)
    print()
    
    # Create graph once and reuse
    print("Initializing LangGraph...")
    try:
        graph = await create_trading_graph()
        print("✅ LangGraph ready")
    except Exception as e:
        print(f"❌ Failed to create graph: {e}")
        return
    
    # Initialize position manager with TradeMind API
    position_manager: Optional[PositionManager] = None
    cache_ttl = settings.position_cache_ttl_seconds if hasattr(settings, 'position_cache_ttl_seconds') else 30
    api_base_url = getattr(settings, 'trademind_api_url', 'http://localhost:8000')
    
    print("Initializing Position Manager with TradeMind API...")
    try:
        position_manager = PositionManager(
            api_base_url=api_base_url,
            cache_ttl_seconds=cache_ttl,
            max_retries=3,
            retry_delay=1.0
        )
        position_manager.take_profit_pct = TAKE_PROFIT_PCT
        position_manager.stop_loss_pct = STOP_LOSS_PCT
        position_manager.max_position_pct = settings.max_position_pct
        await position_manager.fetch_positions()
        print(f"✅ TradeMind API connected (URL: {api_base_url}) and positions loaded")
        print(f"   API Timeout: 90s | Retries: 3 | Cache TTL: {cache_ttl}s")
    except Exception as e:
        print(f"⚠️  TradeMind API connection failed: {e}")
        print(f"   Falling back to simulation mode (no real trading)")
        print(f"   API URL: {api_base_url}")
        position_manager = PositionManager(cache_ttl_seconds=cache_ttl)
        position_manager.take_profit_pct = TAKE_PROFIT_PCT
        position_manager.stop_loss_pct = STOP_LOSS_PCT
        position_manager.max_position_pct = settings.max_position_pct
    
    print()
    
    cycle = 0
    while running:
        cycle += 1
        print(f"\n{'='*70}")
        print(f"🔄 CYCLE #{cycle} - {datetime.now().strftime('%H:%M:%S')}")
        print(f"{'='*70}")
        
        # Fetch fresh positions at start of cycle
        await position_manager.fetch_positions(force_refresh=True)
        position_summary = position_manager.get_position_summary()
        
        print(f"📈 Portfolio Status:")
        print(f"   Value: ${position_summary['portfolio_value']:,.2f}")
        print(f"   Cash: ${position_summary['cash_balance']:,.2f} ({position_summary['cash_pct']:.1%})")
        print(f"   Invested: ${position_summary['invested_value']:,.2f} ({position_summary['invested_pct']:.1%})")
        print(f"   Positions: {position_summary['num_positions']}")
        
         # Check exit triggers for held positions first
        if EXIT_CHECK_ENABLED:
            print(f"\n🎯 Checking exit triggers...")
            for pos_data in position_summary['positions']:
                symbol = pos_data['symbol']
                quantity = pos_data['quantity']
                if quantity == 0:
                    continue
                
                # Debug logging for exit trigger check (Medium Priority Fix #5)
                print(f"   Checking {symbol}: P&L={pos_data['unrealized_pnl_pct']:.1f}%")
                
                should_exit, reason, action = position_manager.check_exit_triggers(symbol)
                if should_exit:
                    print(f"   ⚠️  EXIT SIGNAL: {action} {symbol}")
                    print(f"      Reason: {reason}")
                    
                    # Force refresh positions before exit to ensure fresh data (Critical Fix #3)
                    # This prevents stale position data from being used in exit decisions
                    print(f"   Refreshing position data before exit...")
                    await position_manager.fetch_positions(force_refresh=True)
                    
                    # Execute exit trade with correct symbol parameter (Critical Fix #1)
                    # Ensure symbol flows correctly from watchlist to analysis
                    print(f"   Running exit analysis for {symbol}...")
                    exit_result = await analyze_symbol(
                        graph,
                        symbol,
                        position_manager.to_dict(),
                        position_manager.get_portfolio_value(),
                        position_manager.get_cash_balance(),
                        position_manager.get_sector_exposure_pct()
                    )
                    
                    # Check if analyze_symbol returned valid data before proceeding (Critical Fix #2)
                    # Validate result contains valid decision/confidence, not just error fields
                    # This prevents proceeding with exit when API returns error data
                    if exit_result is None:
                        print(f"   ⚠️  Skipping exit for {symbol}: No analysis result returned")
                        continue
                    
                    is_valid_result = (
                        not exit_result.get('error') and
                        isinstance(exit_result.get('final_action'), str) and
                        isinstance(exit_result.get('confidence'), (int, float))
                    )
                    
                    if not is_valid_result:
                        error_msg = exit_result.get('error', 'Unknown error')
                        print(f"   ⚠️  Skipping exit for {symbol}: Invalid analysis result ({error_msg})")
                        print(f"   Debug: final_action={exit_result.get('final_action')}, confidence={exit_result.get('confidence')}")
                        continue
                    
                    if exit_result.get('execution_status') == 'SUCCESS':
                        print(f"   ✅ Exit executed for {symbol}")
                        # Refresh positions cache after successful trade to prevent stale data
                        await position_manager.fetch_positions(force_refresh=True)
                    else:
                        error_msg = exit_result.get('error') if exit_result else 'Unknown'
                        print(f"   ❌ Exit failed for {symbol}: {error_msg}")
        
        # Analyze watchlist symbols
        print(f"\n📊 Analyzing watchlist...")
        
        position_dict = position_manager.to_dict()
        portfolio_value = position_manager.get_portfolio_value()
        cash_balance = position_manager.get_cash_balance()
        sector_exposure = position_manager.get_sector_exposure_pct()
        
        for symbol in WATCHLIST:
            if not running:
                break
                
            print(f"\n📊 Analyzing {symbol}...")
            
            # Skip if we have a position and it just had exit signal
            if position_manager.has_position(symbol):
                should_exit, reason, _ = position_manager.check_exit_triggers(symbol)
                if should_exit:
                    print(f"   ⏭️  Skipping - exit signal pending")
                    continue
            
            result = await analyze_symbol(
                graph,
                symbol,
                position_dict,
                portfolio_value,
                cash_balance,
                sector_exposure
            )
            
            if not result:
                continue
            
            final_action = result.get('final_action', 'HOLD')
            confidence = result.get('confidence', 0)
            
            print(f"   Decision: {final_action} | Confidence: {confidence:.1%}")
            
            # Position-aware validation
            if final_action == 'SELL':
                if not position_manager.has_position(symbol):
                    print(f"   ⏭️  No action - No position held in {symbol}")
                    continue
                current_qty = position_manager.get_position_quantity(symbol)
                print(f"   Holding: {current_qty} shares")
            
            if final_action == 'BUY':
                # Check cash availability
                decision = result.get('final_decision', {})
                quantity = decision.get('quantity', 0)
                if quantity > 0:
                    is_valid, msg = position_manager.check_cash_availability(symbol, quantity)
                    if not is_valid:
                        print(f"   ⏭️  No action - {msg}")
                        continue
            
            # Check if we should trade
            if final_action in ['BUY', 'SELL'] and confidence >= MIN_CONFIDENCE:
                print(f"   ✅ TRADE SIGNAL: {final_action} {symbol}")
                print(f"      Confidence {confidence:.1%} >= {MIN_CONFIDENCE:.0%}")
                
                if result.get('execution_status') == 'SUCCESS':
                    print(f"   📝 Trade executed!")
                    # Refresh positions after trade
                    await position_manager.fetch_positions(force_refresh=True)
                elif result.get('error'):
                    print(f"   ❌ Trade failed: {result.get('error')}")
                else:
                    print(f"   ⏳ Trade queued (check execution status)")
                    
            else:
                print(f"   ⏭️  No action (decision={final_action}, conf={confidence:.1%})")
        
        if running:
            print(f"\n⏱️  Waiting {CHECK_INTERVAL}s before next cycle...")
            await asyncio.sleep(CHECK_INTERVAL)
    
    print("\n✅ LangGraph Auto-Trader stopped")


if __name__ == "__main__":
    try:
        asyncio.run(run_auto_trader())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
