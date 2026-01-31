# Quick Start Guide

Get your trading bot running in 10 minutes.

## Step 1: Prerequisites

### Required
- Python 3.11 or higher
- IBKR account (paper or live)
- IB Gateway or TWS installed

### Optional
- Docker (for containerized deployment)
- Telegram account (for alerts)

## Step 2: Installation

```bash
cd quant-scalper
./scripts/setup.sh
```

This script will:
- Check for Python 3.11+
- Install Rust (if not present)
- Create a virtual environment
- Install all dependencies
- Build the Rust components

## Step 3: Configuration

### 3.1 Copy Configuration Template
```bash
cp config/config.yaml.example config/config.yaml
```

### 3.2 Get Telegram Credentials (Optional but Recommended)

1. **Create a Telegram Bot**:
   - Message [@BotFather](https://t.me/BotFather) on Telegram
   - Send `/newbot` and follow instructions
   - Save the bot token you receive

2. **Get Your Chat ID**:
   - Message [@userinfobot](https://t.me/userinfobot)
   - It will reply with your chat ID
   - Save this number

### 3.3 Edit Configuration

Open `config/config.yaml` and update:

```yaml
# IBKR Settings
ibkr:
  account: "DU123456"  # Your IBKR paper account ID
  paper: true          # KEEP THIS TRUE for paper trading

# Instruments
instruments:
  - expiry: "202503"   # Update to current front month (YYYYMM)

# Telegram (set via environment variables below)
```

### 3.4 Set Environment Variables

```bash
export TELEGRAM_BOT_TOKEN="1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"
export TELEGRAM_CHAT_ID="123456789"
```

Or add to `~/.bashrc` or `~/.zshrc` for persistence:
```bash
echo 'export TELEGRAM_BOT_TOKEN="your-token"' >> ~/.bashrc
echo 'export TELEGRAM_CHAT_ID="your-chat-id"' >> ~/.bashrc
source ~/.bashrc
```

## Step 4: Start IB Gateway

### Option A: Manual Start
1. Open IB Gateway
2. Login with paper trading credentials
3. Configure API settings:
   - Enable ActiveX and Socket Clients
   - Socket port: 4002 (paper) or 4001 (live)
   - Trusted IP: 127.0.0.1

### Option B: Automated Start (Linux/Mac)
Use IBC (IB Controller) for automated login:
```bash
# Install IBC
# Follow: https://github.com/IbcAlpha/IBC

# Configure IBC with your credentials
# Start IB Gateway via IBC
```

## Step 5: Run the Bot

### Activate Virtual Environment
```bash
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows
```

### Start the Bot
```bash
python -m bot.main config/config.yaml
```

### Expected Output
```
[INFO] Quant Scalper Bot Starting...
[INFO] Loading configuration from config/config.yaml
[INFO] Connecting to IBKR at 127.0.0.1:4002...
[INFO] Connected to IBKR successfully
[INFO] Account: DU123456
[INFO] Subscribing to MES (Micro E-mini S&P 500)
[INFO] Z-Score engine initialized (lookback=20)
[INFO] Trading engine started
[INFO] Telegram alerts enabled
```

## Step 6: Verify It's Working

### Check Telegram
You should receive a message:
```
🤖 Trading Bot Started
Account: DU123456
Mode: PAPER TRADING
Instrument: MES
Strategy: Z-Score Mean Reversion
```

### Monitor Logs
```bash
tail -f logs/bot.log
```

## Step 7: Test Emergency Stop

### Via Telegram
Send message to your bot:
```
/flatten
```

### Via Command Line
```bash
# In another terminal
python -c "
from bot.ibkr.client import IBKRClient
import asyncio

async def flatten():
    client = IBKRClient('127.0.0.1', 4002, 1)
    await client.connect()
    await client.flatten_all()
    await client.disconnect()

asyncio.run(flatten())
"
```

## Common Issues

### "Cannot connect to IBKR"
- Check IB Gateway is running
- Verify port 4002 (paper) or 4001 (live)
- Check firewall settings
- Ensure API is enabled in TWS/Gateway settings

### "Module not found: quant_scalper_rust"
```bash
cd rust
maturin develop --release
cd ..
```

### "Telegram not sending messages"
- Verify bot token and chat ID
- Check environment variables are set
- Try sending a test message to your bot first

### "Invalid contract expiry"
- Update `config/config.yaml` with current front month
- Format: YYYYMM (e.g., "202503" for March 2025)
- Check CME website for rollover dates

## Next Steps

1. **Monitor for 24 hours** - Let it run in paper trading mode
2. **Review logs daily** - Check for errors or warnings
3. **Test recovery** - Kill the bot and restart to verify state recovery
4. **Adjust parameters** - Fine-tune Z-Score thresholds if needed
5. **Paper trade for 3+ months** - Build confidence before going live

## Running in Production

### Using systemd (Linux)
```bash
# Create service file
sudo nano /etc/systemd/system/trading-bot.service

# Add:
[Unit]
Description=Quant Scalper Trading Bot
After=network.target

[Service]
Type=simple
User=yourusername
WorkingDirectory=/path/to/quant-scalper
Environment="TELEGRAM_BOT_TOKEN=your-token"
Environment="TELEGRAM_CHAT_ID=your-chat-id"
ExecStart=/path/to/quant-scalper/venv/bin/python -m bot.main config/config.yaml
Restart=always

[Install]
WantedBy=multi-user.target

# Enable and start
sudo systemctl enable trading-bot
sudo systemctl start trading-bot
sudo systemctl status trading-bot
```

### Using Docker
```bash
# Set environment variables
export TELEGRAM_BOT_TOKEN="your-token"
export TELEGRAM_CHAT_ID="your-chat-id"

# Start with docker-compose
docker-compose up -d

# View logs
docker-compose logs -f trading-bot
```

## Support

- Check `README.md` for detailed documentation
- Review `IMPLEMENTATION_PLAN.md` for development phases
- See emergency procedures in README for troubleshooting

---

**Remember**: Always paper trade for at least 3 months before considering live trading!
