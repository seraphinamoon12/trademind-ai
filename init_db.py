#!/usr/bin/env python3
"""Initialize the database with schema and sample data."""
import sys
from pathlib import Path

# Add project root to path (portable)
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.core.database import init_db, get_db
from src.core.database import MarketData

def main():
    """Initialize database."""
    print("🗄️  Initializing database...")
    init_db()
    print("✅ Database initialized successfully!")

if __name__ == "__main__":
    main()
