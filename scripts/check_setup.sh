#!/bin/bash
# Check if environment is properly set up for the trading bot

echo "🔍 Checking trading bot setup..."
echo "=================================="

# Check Python version
echo ""
echo "📋 Python Version:"
python3 --version
if [ $? -ne 0 ]; then
    echo "❌ Python 3 is not installed"
    exit 1
fi

# Check if virtual environment exists
echo ""
echo "📋 Virtual Environment:"
if [ -d "venv" ]; then
    echo "✅ Virtual environment exists"
    source venv/bin/activate
    echo "   Python: $(python --version)"
else
    echo "⚠️  Virtual environment not found"
    echo "   Run: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
fi

# Check key dependencies
echo ""
echo "📋 Dependencies:"
deps=("ibapi" "pyyaml" "aiohttp")
for dep in "${deps[@]}"; do
    if python -c "import $dep" 2>/dev/null; then
        echo "✅ $dep"
    else
        echo "❌ $dep (not installed)"
    fi
done

# Check Rust
echo ""
echo "📋 Rust:"
if command -v rustc &> /dev/null; then
    echo "✅ Rust installed: $(rustc --version)"
else
    echo "⚠️  Rust not installed (optional - for Z-Score engine)"
fi

# Check configuration
echo ""
echo "📋 Configuration:"
if [ -f "config/config.yaml" ]; then
    echo "✅ config/config.yaml exists"
else
    echo "⚠️  config/config.yaml not found"
    echo "   Run: cp config/config.yaml.example config/config.yaml"
fi

# Check environment variables
echo ""
echo "📋 Environment Variables:"
if [ -n "$TELEGRAM_BOT_TOKEN" ]; then
    echo "✅ TELEGRAM_BOT_TOKEN is set"
else
    echo "⚠️  TELEGRAM_BOT_TOKEN not set"
fi

if [ -n "$TELEGRAM_CHAT_ID" ]; then
    echo "✅ TELEGRAM_CHAT_ID is set"
else
    echo "⚠️  TELEGRAM_CHAT_ID not set"
fi

# Check data directory
echo ""
echo "📋 Directories:"
mkdir -p data logs
echo "✅ Created data/ and logs/ directories"

# Check IBKR connectivity (if configured)
echo ""
echo "📋 IBKR Connection:"
if [ -f "config/config.yaml" ]; then
    echo "   Note: Cannot test IBKR connection without running Gateway"
    echo "   Make sure IB Gateway/TWS is running on port 4002 (paper) or 4001 (live)"
else
    echo "   Skip - no config file"
fi

echo ""
echo "=================================="
echo "✅ Setup check complete!"
echo ""
