#!/bin/bash
# IFSA Market Monitor - Initial Setup Script
set -e

echo "🚀 Setting up IFSA Market Monitor..."

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found. Please install Python 3.11+"
    exit 1
fi

echo "✅ Python found: $(python3 --version)"

# Create virtual env if not exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

echo "📦 Installing dependencies..."
source venv/bin/activate || . venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Create directories
echo "📁 Creating directories..."
mkdir -p data logs

# Copy env example if .env doesn't exist
if [ ! -f ".env" ]; then
    echo "📝 Creating .env from .env.example..."
    cp .env.example .env
    echo "⚠️  Please edit .env with your Telegram/Discord credentials"
else
    echo "✅ .env already exists"
fi

# Check config.yaml
if [ ! -f "config.yaml" ]; then
    echo "❌ config.yaml not found!"
    exit 1
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your credentials:"
echo "   - TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID"
echo "   - DISCORD_WEBHOOK_URL"
echo "2. Run bot: make bot  or  python -m src.bot"
echo "3. Run API: make dev  and open http://localhost:8000/dashboard"
echo "4. Deploy:"
echo "   - Netlify: netlify deploy --prod"
echo "   - Hostinger: make docker-run"
echo ""
