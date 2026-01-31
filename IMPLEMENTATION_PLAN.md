# Implementation Plan - Part 2: Phases & Quick Reference

## Phase 4: Risk Management (1 week) - Continued

| Task | Time | Details |
|------|------|---------|
| Rust RiskCalculator | 4h | Position tracking, P&L |
| Circuit breakers | 6h | Daily loss, consecutive losses |
| Position duration check | 2h | Force close long-held positions |
| State persistence | 4h | Save/load state to JSON |
| Recovery on startup | 4h | Reconcile with IBKR positions |
| Kill switch | 4h | Manual emergency flatten |

**Deliverable:** Risk limits enforced, bot survives restart

### Phase 5: Stability Testing (2 weeks)

| Task | Time | Details |
|------|------|---------|
| Paper trading 24/7 | Ongoing | Monitor for crashes |
| Edge case handling | 8h | Connection drops, order failures |
| Memory leak check | 4h | Profile memory over time |
| Latency monitoring | 4h | Signal-to-order timing |
| Daily review | 1h/day | Check logs, fix issues |
| Stress testing | 4h | High message rates |
| Failover testing | 4h | Kill IB Gateway, verify recovery |

**Deliverable:** 7+ days continuous operation without crashes

### Phase 6: Dashboard (1 week)

| Task | Time | Details |
|------|------|---------|
| FastAPI backend | 4h | Basic REST endpoints |
| Position endpoint | 2h | Current positions |
| Trade history endpoint | 2h | Trade log with filters |
| P&L endpoint | 2h | Daily/weekly/monthly |
| React setup | 2h | Create-react-app, Tailwind |
| Position component | 4h | Display current position |
| P&L chart | 4h | Recharts equity curve |
| Trade table | 4h | Sortable trade history |

**Deliverable:** Basic web dashboard showing positions and P&L

### Phase 7: Backtest & Optimization (1 week)

| Task | Time | Details |
|------|------|---------|
| Historical data fetch | 4h | IBKR reqHistoricalData |
| Backtest engine | 8h | Simulate signals on history |
| Performance metrics | 4h | Win rate, Sharpe, drawdown |
| Parameter sweep | 4h | Test Z-threshold variations |
| Walk-forward test | 4h | Out-of-sample validation |
| Documentation | 4h | Results, optimal parameters |

**Deliverable:** Backtest report with recommended parameters

---

## Quick Start Commands

```bash
# 1. Setup
./scripts/setup.sh

# 2. Configure
cp config/config.yaml.example config/config.yaml
# Edit config/config.yaml with your settings

# 3. Set environment variables
export TELEGRAM_BOT_TOKEN="your-token"
export TELEGRAM_CHAT_ID="your-chat-id"

# 4. Build Rust components
cd rust && maturin develop --release && cd ..

# 5. Run paper trading
python -m bot.main config/config.yaml

# 6. Run with Docker
docker-compose up -d
```

---

## File Checklist

### Must Have for POC
- [x] bot/main.py
- [x] bot/config.py
- [x] bot/core/engine.py
- [x] bot/core/signals.py
- [x] bot/ibkr/client.py
- [x] bot/ibkr/contracts.py
- [x] bot/risk/circuit_breaker.py
- [x] bot/alerts/telegram.py
- [x] bot/persistence/database.py
- [x] rust/src/lib.rs
- [x] rust/src/zscore.rs
- [x] config/config.yaml
- [x] tests/unit/test_zscore.py

### Nice to Have
- [ ] Dashboard (Phase 6)
- [ ] Backtest engine (Phase 7)
- [ ] Telegram commands (/status, /pause)
- [ ] Multiple instruments
- [ ] ML parameter optimization

---

## Risk Checklist (Pre-Live)

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
- [ ] Backup VPS ready (optional)
- [ ] Emergency flatten procedure documented

### Financial
- [ ] Sufficient margin in account
- [ ] Understand MES contract specs
- [ ] Commission costs factored in
- [ ] Tax implications reviewed

### Psychological (Bazi Alignment)
- [ ] Trading as architect, not gambler ✅
- [ ] Earth product built (the bot) ✅
- [ ] Wood fuel active (learning strategies) ✅
- [ ] Fire energy channeled safely ✅
- [ ] Yoga/grounding practice maintained ✅

---

## Emergency Procedures

### Manual Flatten (Telegram)
```
/flatten
```

### Manual Flatten (Command Line)
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

### Kill Everything
```bash
# Stop bot
sudo systemctl stop trading-bot

# Stop IB Gateway
sudo systemctl stop ib-gateway

# Verify no processes
ps aux | grep -E "(python|java)"
```

### Check Positions in TWS
1. Open TWS or IB Gateway web UI
2. Go to Account → Portfolio
3. Verify no open positions
4. If positions exist, manually close them

---

## Support Resources

- IBKR API Documentation: https://interactivebrokers.github.io/tws-api/
- IBC Project: https://github.com/IbcAlpha/IBC
- PyO3 (Rust-Python): https://pyo3.rs/
- MES Contract Specs: https://www.cmegroup.com/markets/equities/sp/micro-e-mini-sandp-500.html

---

## Bazi Reminder

> "This project is not just about making money. It's about building an Earth product that channels Fire energy without burnout."

- **Fire (Coding):** Python, Rust, technical architecture ✓
- **Earth (Product):** The bot itself is an asset ✓
- **Avoid Trading Chaos:** Bot trades, not you ✓
- **Grounding Required:** Systematic approach, paper testing ✓

Stay patient. Paper trade for 3+ months. The bot is the Earth product that protects your wealth.

---

*Last updated: January 2025*
# Quant Scalping Bot 🤖📈

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
- Rust (for building Rust components)
- IBKR account with API access
- IB Gateway or TWS installed

### Installation

```bash
# Clone repository
git clone https://github.com/yourusername/quant-scalper.git
cd quant-scalper

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install Python dependencies
pip install -r requirements.txt

# Build Rust components
pip install maturin
cd rust && maturin develop --release && cd ..

# Copy and edit configuration
cp config/config.yaml.example config/config.yaml
# Edit config/config.yaml with your settings
```

### Configuration

1. Get your IBKR paper trading account ID
2. Get your Telegram bot token from [@BotFather](https://t.me/BotFather)
3. Get your Telegram chat ID from [@userinfobot](https://t.me/userinfobot)
4. Set environment variables:

```bash
export TELEGRAM_BOT_TOKEN="your-bot-token"
export TELEGRAM_CHAT_ID="your-chat-id"
```

### Running

```bash
# Start IB Gateway first
# Then run the bot:
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
└── docs/                   # Documentation
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

## Safety Notes

⚠️ **IMPORTANT**:
1. **Paper trade for at least 3 months** before considering live trading
2. Never trade with money you can't afford to lose
3. The bot is a tool - it's not guaranteed to make money
4. Always monitor the bot, especially in the early stages

## Bazi Alignment 🔥

This bot is designed as an "Earth product" to:
- Channel Fire energy (coding) into a tangible asset
- Remove emotional trading decisions
- Provide systematic, grounded approach to markets
- Support the builder's King/Queen energy without burnout

## License

MIT License - See LICENSE file

## Disclaimer

This software is for educational purposes only. Trading futures involves substantial risk of loss and is not suitable for all investors. Past performance is not indicative of future results.
