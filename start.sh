#!/bin/bash
# Start the Trading Agent application

cd /home/seraphina-moon/projects/trading-agent
source venv/bin/activate

echo "🚀 Starting TradeMind AI..."
echo ""

# Check if Docker containers are running
if ! docker ps | grep -q trading-agent-db; then
    echo "📦 Starting Docker containers..."
    docker compose up -d
    sleep 3
fi

# Initialize database
echo "🗄️  Initializing database..."
python3 -c "
from src.core.database import init_db
init_db()
print('✅ Database ready')
"

# Ingest sample data if needed
echo "📥 Checking market data..."
python3 -c "
from src.data.ingestion import ingestion
from src.core.database import get_db
db = next(get_db())
from src.core.database import MarketData
count = db.query(MarketData).count()
if count == 0:
    print('Ingesting sample data...')
    symbols = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA']
    for symbol in symbols:
        ingestion.ingest_symbol(symbol, db=db)
    print(f'✅ Ingested data for {len(symbols)} symbols')
else:
    print(f'✅ Found {count} market data records')
" 2>/dev/null

echo ""
echo "🌐 Starting web server on http://localhost:8000"
echo ""

# Start the server
exec uvicorn src.main:app --host 0.0.0.0 --port 8000
