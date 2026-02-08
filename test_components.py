#!/usr/bin/env python3
"""Quick test script for trading agent components."""
import sys
sys.path.insert(0, '/home/seraphina-moon/projects/trading-agent')
from sqlalchemy import text

print("🧪 Testing Trading Agent Components...\n")

# Test 1: Config
print("1️⃣ Testing Configuration...")
try:
    from src.config import settings
    print(f"   ✅ App name: {settings.app_name}")
    print(f"   ✅ Database URL: {settings.database_url}")
    print(f"   ✅ Redis URL: {settings.redis_url}")
except Exception as e:
    print(f"   ❌ Config error: {e}")

# Test 2: Database Connection
print("\n2️⃣ Testing Database Connection...")
try:
    from src.core.database import engine
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version();"))
        version = result.fetchone()[0]
        print(f"   ✅ Connected: {version[:50]}...")
except Exception as e:
    print(f"   ❌ Database error: {e}")

# Test 3: Redis Connection  
print("\n3️⃣ Testing Redis Connection...")
try:
    from src.core.cache import cache
    cache.set("test_key", "test_value", 10)
    value = cache.get("test_key")
    if value == "test_value":
        print("   ✅ Redis working")
    else:
        print("   ❌ Redis value mismatch")
except Exception as e:
    print(f"   ❌ Redis error: {e}")

# Test 4: Data Provider
print("\n4️⃣ Testing Data Provider (Yahoo Finance)...")
try:
    from src.data.providers import yahoo_provider
    df = yahoo_provider.get_historical("AAPL", period="5d")
    if df is not None and not df.empty:
        print(f"   ✅ Fetched {len(df)} days of AAPL data")
        print(f"   ✅ Latest price: ${df['close'].iloc[-1]:.2f}")
    else:
        print("   ❌ No data received")
except Exception as e:
    print(f"   ❌ Provider error: {e}")

# Test 5: Indicators
print("\n5️⃣ Testing Technical Indicators...")
try:
    from src.data.indicators import TechnicalIndicators
    from src.data.providers import yahoo_provider
    
    df = yahoo_provider.get_historical("AAPL", period="30d")
    if df is not None:
        df_ind = TechnicalIndicators.add_all_indicators(df)
        signals = TechnicalIndicators.get_latest_signals(df_ind)
        print(f"   ✅ RSI: {signals.get('rsi', 'N/A'):.2f}")
        print(f"   ✅ Signal: {signals.get('rsi_signal', 'N/A')}")
except Exception as e:
    print(f"   ❌ Indicators error: {e}")

# Test 6: Strategies
print("\n6️⃣ Testing Strategies...")
try:
    from src.strategies.rsi_reversion import RSIMeanReversionStrategy
    from src.strategies.ma_crossover import MACrossoverStrategy
    from src.data.providers import yahoo_provider
    
    df = yahoo_provider.get_historical("AAPL", period="1y")
    
    rsi_strat = RSIMeanReversionStrategy()
    rsi_signal = rsi_strat.generate_signal(df, "AAPL")
    if rsi_signal:
        print(f"   ✅ RSI Strategy: {rsi_signal.signal.value} (confidence: {rsi_signal.confidence})")
    else:
        print(f"   ℹ️ RSI Strategy: No signal")
    
    ma_strat = MACrossoverStrategy()
    ma_signal = ma_strat.generate_signal(df, "AAPL")
    if ma_signal:
        print(f"   ✅ MA Strategy: {ma_signal.signal.value} (confidence: {ma_signal.confidence})")
    else:
        print(f"   ℹ️ MA Strategy: No signal")
except Exception as e:
    print(f"   ❌ Strategy error: {e}")

# Test 7: Agents
print("\n7️⃣ Testing Agents...")
try:
    from src.agents.technical import TechnicalAgent
    from src.agents.risk import RiskAgent
    from src.data.providers import yahoo_provider
    
    df = yahoo_provider.get_historical("AAPL", period="90d")
    
    tech_agent = TechnicalAgent()
    signal = tech_agent.analyze("AAPL", df)
    print(f"   ✅ Technical Agent: {signal.decision.value}")
    
    risk_agent = RiskAgent()
    risk_signal = risk_agent.analyze("AAPL", df, portfolio_value=100000)
    print(f"   ✅ Risk Agent: {risk_signal.decision.value}")
except Exception as e:
    print(f"   ❌ Agent error: {e}")

# Test 8: Backtest Engine
print("\n8️⃣ Testing Backtest Engine...")
try:
    from src.backtest.engine import BacktestEngine
    from src.strategies.rsi_reversion import RSIMeanReversionStrategy
    from src.data.providers import yahoo_provider
    
    df = yahoo_provider.get_historical("AAPL", period="1y")
    strat = RSIMeanReversionStrategy()
    engine = BacktestEngine(initial_cash=100000)
    
    results = engine.run(df, "AAPL", strat.generate_signal)
    print(f"   ✅ Total Return: {results.get('total_return_pct', 0):.2f}%")
    sharpe = results.get('sharpe_ratio')
    print(f"   ✅ Sharpe Ratio: {sharpe:.2f}" if sharpe else "   ℹ️ Sharpe Ratio: N/A")
    print(f"   ✅ Trades: {results.get('total_trades', 0)}")
except Exception as e:
    print(f"   ❌ Backtest error: {e}")

print("\n🎉 Component testing complete!")
