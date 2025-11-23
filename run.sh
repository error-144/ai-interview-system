#!/bin/bash

# AI Interview System Startup Script

echo "🚀 Starting AI Interview System..."
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install Python dependencies
echo "📥 Installing Python dependencies..."
pip install -r requirements.txt

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found. Creating from .env.example..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "✅ Created .env file. Please add your OPENAI_API_KEY!"
    else
        echo "OPENAI_API_KEY=your_api_key_here" > .env
        echo "LLM_MODEL=gpt-4o-mini" >> .env
        echo "✅ Created .env file. Please add your OPENAI_API_KEY!"
    fi
fi

# Install frontend dependencies if needed
if [ ! -d "frontend/node_modules" ]; then
    echo "📥 Installing frontend dependencies..."
    cd frontend
    npm install
    cd ..
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "To start the application:"
echo "  1. Backend:  python api.py (or uvicorn api:app --reload)"
echo "  2. Frontend: cd frontend && npm run dev"
echo ""
echo "Backend will run on http://localhost:8000"
echo "Frontend will run on http://localhost:3000"

