#!/bin/bash
# Start the Trading Agent application

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Activate virtual environment (check multiple locations)
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
elif [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
else
    echo "❌ Virtual environment not found. Please create one:"
    echo "   python3 -m venv venv"
    echo "   source venv/bin/activate"
    echo "   pip install -r requirements.txt"
    exit 1
fi

echo "🚀 Starting TradeMind AI..."
echo ""

# Check if Docker containers are running (optional)
if command -v docker >/dev/null 2>&1; then
    if ! docker ps | grep -q "trading-agent-db\|redis"; then
        echo "📦 Starting Docker containers..."
        docker compose up -d 2>/dev/null || docker-compose up -d 2>/dev/null || echo "   (Docker compose not configured, skipping)"
        sleep 3
    fi
fi

# Initialize database
echo "🗄️  Initializing database..."
python3 -c "
from src.core.database import init_db
init_db()
print('✅ Database ready')
" 2>/dev/null || echo "   (Database initialization skipped)"

echo ""
echo "🌐 Starting web server on http://localhost:8000"
echo ""

# Start the server
exec uvicorn src.main:app --host 0.0.0.0 --port 8000
