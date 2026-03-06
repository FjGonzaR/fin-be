#!/bin/bash
# Setup script for Finanzas Backend

echo "🚀 Setting up Finanzas Backend..."

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "✓ Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -e .

echo ""
echo "✓ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Start PostgreSQL: docker-compose up -d"
echo "2. Activate venv: source venv/bin/activate"
echo "3. Run migrations: alembic upgrade head"
echo "4. Create account: python scripts/create_account.py"
echo "5. Start API: uvicorn app.main:app --reload"
