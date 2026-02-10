#!/bin/bash
# setup_env.sh - Setup environment variables for TradeMind AI
# Run this script to configure your API keys and sensitive settings

echo "=================================="
echo "TradeMind AI - Environment Setup"
echo "=================================="
echo ""

# Check if .env already exists
if [ -f ".env" ]; then
    echo "⚠️  .env file already exists!"
    read -p "Do you want to overwrite it? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Setup cancelled."
        exit 1
    fi
fi

# Copy example file
cp .env.example .env

echo "✅ Created .env file from template"
echo ""
echo "Please edit .env and fill in your values:"
echo ""
echo "Required:"
echo "  - ZAI_API_KEY (for sentiment analysis)"
echo "  - IBKR_ACCOUNT (your paper trading account ID)"
echo ""
echo "Optional:"
echo "  - OPENAI_API_KEY (alternative to ZAI)"
echo "  - LANGSMITH_API_KEY (for observability)"
echo "  - WEBSOCKET_AUTH_TOKEN (generate a secure random string)"
echo "  - DB_PASSWORD (PostgreSQL password)"
echo ""
echo "To generate a secure token for WEBSOCKET_AUTH_TOKEN, run:"
echo "  openssl rand -base64 32"
echo ""
echo "After editing .env, load it with:"
echo "  source .env"
