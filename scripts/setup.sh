#!/bin/bash
# Automated setup script for Quant Scalping Bot

set -e  # Exit on error

echo "=========================================="
echo "🤖 Quant Scalping Bot - Setup"
echo "=========================================="
echo ""

# 1. Check Python version
echo "1️⃣  Checking Python version..."
python3 --version || (echo "❌ Python 3 not found" && exit 1)

# 2. Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo ""
    echo "2️⃣  Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "2️⃣  Virtual environment already exists"
fi

# 3. Activate virtual environment
echo ""
echo "3️⃣  Activating virtual environment..."
source venv/bin/activate

# 4. Upgrade pip
echo ""
echo "4️⃣  Upgrading pip..."
pip install --upgrade pip setuptools wheel

# 5. Install Python dependencies
echo ""
echo "5️⃣  Installing Python dependencies..."
pip install -r requirements.txt

# 6. Create necessary directories
echo ""
echo "6️⃣  Creating directories..."
mkdir -p data logs

# 7. Check if config exists
if [ ! -f "config/config.yaml" ]; then
    echo ""
    echo "7️⃣  Copying config template..."
    cp config/config.yaml.example config/config.yaml
    echo "✅ Created config/config.yaml"
    echo "   ⚠️  Please edit config/config.yaml with your settings!"
else
    echo "7️⃣  Config file already exists"
fi

# 8. Check environment variables
echo ""
echo "8️⃣  Checking environment variables..."
if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo "⚠️  TELEGRAM_BOT_TOKEN not set"
    echo "   Run: export TELEGRAM_BOT_TOKEN=\"your-token\""
else
    echo "✅ TELEGRAM_BOT_TOKEN is set"
fi

if [ -z "$TELEGRAM_CHAT_ID" ]; then
    echo "⚠️  TELEGRAM_CHAT_ID not set"
    echo "   Run: export TELEGRAM_CHAT_ID=\"your-chat-id\""
else
    echo "✅ TELEGRAM_CHAT_ID is set"
fi

# 9. Test imports
echo ""
echo "9️⃣  Testing Python imports..."
python3 << 'PYTHON'
import sys
try:
    import ibapi
    import yaml
    print("✅ Core imports OK")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

# Try optional imports
try:
    import aiohttp
    print("✅ Telegram dependencies OK")
except ImportError:
    print("⚠️  aiohttp not installed (Telegram alerts disabled)")

PYTHON

# 10. Summary
echo ""
echo "=========================================="
echo "✅ Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Edit config/config.yaml with your IBKR account details"
echo "  2. Set environment variables for Telegram alerts"
echo "  3. Run: python3 -m bot.core.signals (test signal generation)"
echo "  4. Run: python3 -m bot.persistence.database (test database)"
echo "  5. When ready: python -m bot.main config/config.yaml"
echo ""
