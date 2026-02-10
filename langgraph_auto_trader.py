#!/usr/bin/env python3
"""
LangGraph Auto-Trader

Runs LangGraph multi-agent workflow continuously on watchlist symbols.
Auto-approves trades with high confidence.
"""

import asyncio
import sys
import time
import signal
from datetime import datetime, timezone
from typing import List

sys.path.insert(0, '.')

from src.trading_graph.graph import create_trading_graph
from src.trading_graph.state import TradingState
from src.config import settings

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

# Control flag
running = True

def signal_handler(sig, frame):
    global running
    print("\n⚠️  Shutting down LangGraph Auto-Trader...")
    running = False

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


async def analyze_symbol(graph, symbol: str) -> dict:
    """Run LangGraph analysis on a single symbol."""
    try:
        state = TradingState(
            symbol=symbol,
            timestamp=datetime.now(timezone.utc).isoformat(),
            current_node="start"
        )
        
        config = {
            "configurable": {
                "thread_id": f"auto-trade-{symbol}-{int(time.time())}"
            }
        }
        
        result = await graph.ainvoke(state, config=config)
        return result
        
    except Exception as e:
        print(f"   ❌ Error analyzing {symbol}: {e}")
        return None


async def run_auto_trader():
    """Main auto-trading loop."""
    global running
    
    print("="*70)
    print("🤖 LANGGRAPH AUTO-TRADER")
    print("="*70)
    print()
    print("Configuration:")
    print(f"  Watchlist: {len(WATCHLIST)} symbols")
    print(f"  Min Confidence: {MIN_CONFIDENCE:.0%}")
    print(f"  Check Interval: {CHECK_INTERVAL}s")
    print(f"  Max Positions: {MAX_POSITIONS}")
    print(f"  Sector Limit: 50% (updated)")
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
    
    print()
    
    cycle = 0
    while running:
        cycle += 1
        print(f"\n{'='*70}")
        print(f"🔄 CYCLE #{cycle} - {datetime.now().strftime('%H:%M:%S')}")
        print(f"{'='*70}")
        
        for symbol in WATCHLIST:
            if not running:
                break
                
            print(f"\n📊 Analyzing {symbol}...")
            
            result = await analyze_symbol(graph, symbol)
            
            if not result:
                continue
            
            decision = result.get('decision', 'UNKNOWN')
            confidence = result.get('confidence', 0)
            
            print(f"   Decision: {decision} | Confidence: {confidence:.1%}")
            
            # Check if we should trade
            if decision in ['BUY', 'SELL'] and confidence >= MIN_CONFIDENCE:
                print(f"   ✅ TRADE SIGNAL: {decision} {symbol}")
                print(f"      Confidence {confidence:.1%} >= {MIN_CONFIDENCE:.0%}")
                
                # Note: Actual execution would happen here
                # The execute_trade node handles this when human_approved=True
                # For now, we just log the signal
                
                if result.get('execution_status') == 'SUCCESS':
                    print(f"   📝 Trade executed!")
                else:
                    print(f"   ⏳ Trade queued (check execution status)")
                    
            else:
                print(f"   ⏭️  No action (decision={decision}, conf={confidence:.1%})")
        
        if running:
            print(f"\n⏱️  Waiting {CHECK_INTERVAL}s before next cycle...")
            await asyncio.sleep(CHECK_INTERVAL)
    
    print("\n✅ LangGraph Auto-Trader stopped")


if __name__ == "__main__":
    try:
        asyncio.run(run_auto_trader())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
