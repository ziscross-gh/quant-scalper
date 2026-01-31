# Quant Scalping Bot

An automated futures scalping bot using Interactive Brokers API with Z-Score mean reversion strategy.

## Features

- **Z-Score Mean Reversion**: Statistical arbitrage based on price deviation from rolling mean
- **Rust Core**: High-performance Z-Score calculation (~50x faster than NumPy)
- **Risk Management**: Circuit breakers, daily loss limits, position duration limits
- **Telegram Alerts**: Real-time notifications for trades, errors, and daily summaries
- **Paper Trading First**: Built for 3+ months of paper trading before going live

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    Telegram     │     │   Python Bot    │     │   Rust Engine   │
│    Alerts       │◄────│     Core        │────►│   (Z-Score)     │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                        ┌────────▼────────┐
                        │   IB Gateway    │
                        └────────┬────────┘
                                 │
                        ┌────────▼────────┐
                        │   IBKR Paper    │
                        │   or Live       │
                        └─────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.11+
- Rust (automatically installed by setup script)
- IBKR account with API access
- IB Gateway or TWS installed

### Installation

```bash
# Clone or navigate to the project
cd quant-scalper

# Run setup script
./scripts/setup.sh

# Activate virtual environment
source venv/bin/activate

# Configure the bot
cp config/config.yaml.example config/config.yaml
# Edit config/config.yaml with your settings
```

### Configuration

1. **IBKR Account**: Get your paper trading account ID
2. **Telegram Bot**:
   - Get token from [@BotFather](https://t.me/BotFather)
   - Get chat ID from [@userinfobot](https://t.me/userinfobot)
3. **Set Environment Variables**:

```bash
export TELEGRAM_BOT_TOKEN="your-bot-token"
export TELEGRAM_CHAT_ID="your-chat-id"
```

4. **Update Futures Expiry**: Edit `config/config.yaml` and update the MES contract expiry to the current front month (format: YYYYMM)

### Running

```bash
# Start IB Gateway first (port 4002 for paper trading)

# Run the bot
python -m bot.main config/config.yaml
```

## Trading Strategy

### Z-Score Mean Reversion

The bot uses Z-Score to identify statistically significant price deviations:

```
Z-Score = (Current Price - Rolling Mean) / Rolling Std Dev
```

**Trading Rules:**

| Z-Score | Action |
|---------|--------|
| ≥ +2.0 | Short (price overextended) |
| ≤ -2.0 | Long (price oversold) |
| Returns to ±0.5 | Exit position |

### Risk Management

- **Stop Loss**: $200 per contract
- **Take Profit**: $300 per contract
- **Daily Loss Limit**: $500 (circuit breaker)
- **Consecutive Losses**: 3 (triggers 30-minute pause)
- **Position Duration**: 2 hours max

## Project Structure

```
quant-scalper/
├── bot/                    # Python trading bot
│   ├── core/              # Trading engine, signals
│   ├── ibkr/              # IBKR API integration
│   ├── risk/              # Risk management
│   ├── alerts/            # Telegram notifications
│   ├── persistence/       # Database, state
│   └── utils/             # Helpers
├── rust/                   # High-performance components
│   └── src/
│       ├── zscore.rs      # Z-Score engine
│       └── risk_calculator.rs
├── config/                 # Configuration files
├── tests/                  # Test suite
├── scripts/               # Setup and utility scripts
├── logs/                  # Log files
└── data/                  # Database and state files
```

## Development

### Running Tests

```bash
# Python tests
pytest tests/ -v

# Rust tests
cd rust && cargo test
```

### Building for Production

```bash
# Build optimized Rust wheel
cd rust && maturin build --release
```

## Implementation Phases

The bot is built in phases (see IMPLEMENTATION_PLAN.md for details):

1. ✅ **Foundation**: Core architecture, IBKR connection
2. ✅ **Z-Score Engine**: Rust implementation
3. ✅ **Basic Trading**: Signal generation, order execution
4. ✅ **Risk Management**: Circuit breakers, position limits
5. ⏳ **Stability Testing**: 2 weeks of continuous operation
6. 📋 **Dashboard**: Web UI for monitoring
7. 📋 **Backtest**: Historical validation

## Safety Notes

⚠️ **IMPORTANT**:

1. **Paper trade for at least 3 months** before considering live trading
2. Never trade with money you can't afford to lose
3. The bot is a tool - it's not guaranteed to make money
4. Always monitor the bot, especially in the early stages
5. Test all emergency procedures (flatten, kill switch) regularly

## Pre-Live Checklist

Before going live, verify ALL of these:

### Technical
- [ ] Paper traded for 3+ months
- [ ] Win rate > 45%
- [ ] Profit factor > 1.2
- [ ] Max drawdown < 10%
- [ ] 0 crashes in last 30 days
- [ ] Recovery tested (kill -9, restart)
- [ ] IB Gateway auto-reconnect tested
- [ ] Circuit breakers tested manually

### Operational
- [ ] Telegram alerts working
- [ ] Daily summary reports received
- [ ] VPS monitoring setup
- [ ] Emergency flatten procedure documented

### Financial
- [ ] Sufficient margin in account
- [ ] Understand MES contract specs
- [ ] Commission costs factored in
- [ ] Tax implications reviewed

## Emergency Procedures

### Manual Flatten via Telegram
```
/flatten
```

### Manual Flatten via Command Line
```bash
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

## Support Resources

- [IBKR API Documentation](https://interactivebrokers.github.io/tws-api/)
- [MES Contract Specs](https://www.cmegroup.com/markets/equities/sp/micro-e-mini-sandp-500.html)
- [PyO3 (Rust-Python)](https://pyo3.rs/)

## License

MIT License - See LICENSE file

## Disclaimer

This software is for educational purposes only. Trading futures involves substantial risk of loss and is not suitable for all investors. Past performance is not indicative of future results.

---

**Remember**: This bot is an "Earth product" designed to channel Fire energy (coding) into a systematic, grounded trading approach. Stay patient, paper trade thoroughly, and let the bot do the trading - not you.
