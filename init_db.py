#!/usr/bin/env python3
"""Initialize database and ingest sample data."""
import sys
sys.path.insert(0, '/home/seraphina-moon/projects/trading-agent')

from src.core.database import init_db, get_db, MarketData
from src.data.ingestion import ingestion
from src.config import settings

print("🚀 Initializing Trading Agent Database...")

# Initialize database
try:
    init_db()
    print("✅ Database initialized with TimescaleDB hypertables")
except Exception as e:
    print(f"❌ Database initialization failed: {e}")
    sys.exit(1)

# Ingest sample data for watchlist symbols
print(f"\n📥 Ingesting market data for {len(settings.watchlist)} symbols...")
sample_symbols = settings.watchlist[:5]  # Start with first 5

for symbol in sample_symbols:
    try:
        count = ingestion.ingest_symbol(symbol, period="1y")
        print(f"  ✅ {symbol}: {count} records")
    except Exception as e:
        print(f"  ❌ {symbol}: {e}")

print("\n🎉 Initialization complete!")
print(f"   Database: {settings.database_url}")
print(f"   Symbols: {', '.join(sample_symbols)}")
