#!/bin/bash
# Quant Scalper Setup Script

set -e

echo "🚀 Setting up Quant Scalper Trading Bot..."

# Check Python version
if ! command -v python3.11 &> /dev/null; then
    echo "⚠️  Python 3.11+ not found. Please install Python 3.11 or later."
    exit 1
fi

# Check Rust
if ! command -v cargo &> /dev/null; then
    echo "⚠️  Rust not found. Installing Rust..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    source "$HOME/.cargo/env"
fi

# Create virtual environment
echo "📦 Creating virtual environment..."
python3.11 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install Python dependencies
echo "📥 Installing Python dependencies..."
pip install -r requirements.txt

# Install Rust build tool
echo "🦀 Installing maturin..."
pip install maturin

# Build Rust components
echo "🔨 Building Rust components..."
cd rust
maturin develop --release
cd ..

# Create necessary directories
echo "📁 Creating data directories..."
mkdir -p logs data

# Create .gitignore
echo "📝 Creating .gitignore..."
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
ENV/

# Rust
/rust/target/
Cargo.lock

# Data
logs/*.log
data/*.db
data/*.csv
*.sqlite

# Config with secrets
config/config.yaml

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Backup
*.bak
EOF

echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Activate virtual environment: source venv/bin/activate"
echo "2. Copy config template: cp config/config.yaml.example config/config.yaml"
echo "3. Edit config/config.yaml with your IBKR and Telegram credentials"
echo "4. Set environment variables for Telegram:"
echo "   export TELEGRAM_BOT_TOKEN='your-token'"
echo "   export TELEGRAM_CHAT_ID='your-chat-id'"
echo "5. Run the bot: python -m bot.main config/config.yaml"
