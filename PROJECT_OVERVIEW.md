# Quant Scalper - Project Overview

**Created**: January 31, 2026
**Version**: 1.0.0-POC
**Status**: Paper Trading Phase

## What Is This?

An automated futures trading bot that uses statistical Z-Score mean reversion to trade Micro E-mini S&P 500 (MES) contracts through Interactive Brokers.

## Key Features

- **High-Performance Rust Core**: Z-Score calculations ~50x faster than pure Python
- **Risk Management**: Multiple circuit breakers and position limits
- **Telegram Integration**: Real-time alerts and emergency controls
- **Paper Trading First**: Designed for 3+ months of testing before live trading
- **Systematic Approach**: Removes emotional decision-making from trading

## Project Structure

```
quant-scalper/
├── bot/                        # Python trading bot
│   ├── alerts/                # Telegram notifications
│   │   ├── __init__.py
│   │   └── telegram.py        # Alert system (complete)
│   ├── core/                  # Trading engine
│   │   └── __init__.py        # TODO: Implement engine.py, signals.py
│   ├── ibkr/                  # IBKR API integration
│   │   └── __init__.py        # TODO: Implement client.py, contracts.py
│   ├── risk/                  # Risk management
│   │   └── __init__.py        # TODO: Implement circuit_breaker.py
│   ├── persistence/           # Database and state
│   │   └── __init__.py        # TODO: Implement database.py
│   ├── utils/                 # Helper functions
│   │   ├── __init__.py
│   │   └── timezone.py        # Timezone utilities (complete)
│   └── __init__.py
│
├── rust/                       # High-performance components
│   ├── src/
│   │   ├── lib.rs            # Rust-Python bindings (complete)
│   │   ├── zscore.rs         # Z-Score engine (complete, tested)
│   │   └── risk_calculator.rs # Risk calculations (complete)
│   └── Cargo.toml            # Rust dependencies
│
├── config/
│   └── config.yaml.example   # Configuration template
│
├── tests/
│   ├── unit/                 # Unit tests
│   └── integration/          # Integration tests
│
├── scripts/
│   └── setup.sh              # Automated setup script
│
├── logs/                      # Log files (gitignored)
├── data/                      # Database files (gitignored)
│
└── Documentation
    ├── README.md              # Main documentation
    ├── QUICKSTART.md          # 10-minute setup guide
    ├── IMPLEMENTATION_PLAN.md # Development phases
    ├── CONTRIBUTING.md        # Contribution guidelines
    └── PROJECT_OVERVIEW.md    # This file

```

## Implementation Status

### ✅ Completed (Phase 1-3)
- [x] Project structure
- [x] Rust Z-Score engine (fully tested)
- [x] Rust risk calculator
- [x] Telegram alert system
- [x] Timezone utilities
- [x] Configuration system
- [x] Docker support
- [x] Setup scripts
- [x] Documentation

### 🚧 In Progress
- [ ] IBKR client implementation
- [ ] Trading engine core
- [ ] Signal generation
- [ ] Circuit breaker system
- [ ] Database persistence
- [ ] Main entry point (bot.main)

### 📋 Planned
- [ ] Stability testing (2 weeks continuous)
- [ ] Web dashboard (FastAPI + React)
- [ ] Backtest engine
- [ ] Parameter optimization

## Current Development Phase

**Phase 3-4**: Completing core trading functionality

According to `IMPLEMENTATION_PLAN.md`, the next tasks are:

1. **IBKR Client** (`bot/ibkr/client.py`)
   - Connection management
   - Order execution
   - Position tracking
   - Market data subscription

2. **Trading Engine** (`bot/core/engine.py`)
   - Main event loop
   - Signal processing
   - Order management
   - State machine

3. **Signal Generator** (`bot/core/signals.py`)
   - Z-Score signal logic
   - Entry/exit conditions
   - Position sizing

4. **Circuit Breaker** (`bot/risk/circuit_breaker.py`)
   - Daily loss limits
   - Consecutive loss tracking
   - Trading pauses

5. **Database** (`bot/persistence/database.py`)
   - Trade logging
   - State persistence
   - Performance tracking

## Quick Start

```bash
# 1. Setup
cd quant-scalper
./scripts/setup.sh

# 2. Configure
cp config/config.yaml.example config/config.yaml
# Edit config/config.yaml with your IBKR account details

# 3. Set environment variables
export TELEGRAM_BOT_TOKEN="your-token"
export TELEGRAM_CHAT_ID="your-chat-id"

# 4. Run (once implementation is complete)
source venv/bin/activate
python -m bot.main config/config.yaml
```

See `QUICKSTART.md` for detailed instructions.

## Architecture Decisions

### Why Rust for Z-Score?
- **Performance**: ~50x faster than NumPy for rolling calculations
- **Reliability**: Memory safety prevents crashes
- **Learning**: Educational value in cross-language integration

### Why Telegram for Alerts?
- **Accessibility**: Works on any device
- **Reliability**: Better than email for time-sensitive alerts
- **Emergency Control**: Can send commands remotely

### Why MES (Micro E-mini S&P 500)?
- **Lower Risk**: 1/10 the size of standard E-mini
- **Liquidity**: Tight spreads, good for scalping
- **Hours**: Nearly 24-hour trading
- **Margin**: More accessible for smaller accounts

## Risk Management Philosophy

This bot prioritizes **capital preservation** over returns:

1. **Multiple Safeguards**: Circuit breakers at multiple levels
2. **Position Limits**: Max 2 contracts, 2-hour duration
3. **Daily Limits**: $500 max daily loss
4. **Emergency Stops**: Multiple ways to flatten positions
5. **Paper Trading**: Mandatory 3+ month testing period

## Development Roadmap

### Week 1-2: Core Implementation
- Complete IBKR client
- Build trading engine
- Implement circuit breakers
- Add database persistence

### Week 3-4: Testing
- Unit tests for all components
- Integration tests with IBKR paper
- Edge case handling
- Memory leak testing

### Month 2-4: Stability
- 24/7 paper trading
- Performance monitoring
- Bug fixes and optimization
- Daily review and adjustment

### Month 4+: Enhancement
- Web dashboard
- Backtest engine
- Parameter optimization
- Additional strategies

## Safety Reminders

⚠️ **CRITICAL**:
- Always start with **paper trading**
- Never risk more than you can afford to lose
- Test all emergency procedures regularly
- Monitor the bot actively in early stages
- This is educational software, not financial advice

## Files You Need to Configure

1. **config/config.yaml** - Copy from `config.yaml.example` and fill in:
   - IBKR account ID
   - Contract expiry (update monthly)
   - Risk parameters

2. **Environment Variables** - Set these:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`

## Getting Help

- **Setup Issues**: See `QUICKSTART.md`
- **Development**: See `IMPLEMENTATION_PLAN.md`
- **Contributing**: See `CONTRIBUTING.md`
- **General Info**: See `README.md`

## Next Steps

If you're starting development:
1. Review `IMPLEMENTATION_PLAN.md` for detailed tasks
2. Start with `bot/ibkr/client.py` implementation
3. Write tests as you go
4. Use paper trading for all testing

If you're setting up for paper trading:
1. Follow `QUICKSTART.md`
2. Verify all tests pass: `pytest`
3. Test emergency procedures
4. Monitor for 24 hours before trusting it

---

**Philosophy**: This bot is an "Earth product" - a tangible asset built through Fire energy (coding). It provides a systematic, grounded approach to trading while removing emotional decision-making. Stay patient, test thoroughly, and let the system work.

**Last Updated**: January 31, 2026
