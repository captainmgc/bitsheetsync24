#!/bin/bash
# Backend Setup Script

set -e

echo "🚀 Setting up Bitrix24 Export Backend..."

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate venv
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "📚 Installing dependencies..."
pip install -r requirements.txt

# Copy .env if doesn't exist
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file..."
    cp .env.example .env
    echo "⚠️  Please edit .env with your configuration"
fi

# Run migrations
echo "🗄️  Running database migrations..."
psql postgresql://bitsheet:bitsheet123@localhost:5432/bitsheet_db -f migrations/001_create_export_tables.sql

echo "✅ Backend setup complete!"
echo ""
echo "To start the server:"
echo "  source venv/bin/activate"
echo "  python -m app.main"
echo ""
echo "Or use uvicorn directly:"
echo "  uvicorn app.main:app --reload"
