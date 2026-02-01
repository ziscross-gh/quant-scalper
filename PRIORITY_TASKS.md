# Priority Task List - Quant Scalper

**Last Updated**: January 31, 2026
**Current Status**: Phase 0 Complete (Bug Fixes Done)
**Next Phase**: Implementation of Core Modules

---

## 🎯 Critical Path to Working Bot (MVP)

This is the **absolute minimum** needed for a working paper trading bot, ordered by dependency.

### Priority 1: Configuration (BLOCKING ALL OTHER WORK)
**Estimated Time**: 4-6 hours
**Why First**: Every other module needs config

- **Task 1.1**: Implement `bot/config.py`
  - [ ] Define config data structures (Pydantic models or dataclasses)
  - [ ] Load YAML file with PyYAML
  - [ ] Substitute environment variables (`${TELEGRAM_BOT_TOKEN}`)
  - [ ] Validate all required fields
  - [ ] Add `get_config()` singleton function
  - [ ] Write 10+ unit tests
  - **Deliverable**: Can load `config/config.yaml.example` successfully

### Priority 2: Contract Definition (SIMPLE, QUICK WIN)
**Estimated Time**: 2-3 hours
**Why Second**: IBKR client needs this immediately

- **Task 1.2**: Implement `bot/ibkr/contracts.py`
  - [ ] `create_mes_contract(expiry: str) -> Contract` function
  - [ ] Contract validation helper
  - [ ] Front-month expiry calculator
  - [ ] Rollover date helper
  - [ ] Write 5+ unit tests
  - **Deliverable**: Can create valid MES contract object

---

### Priority 3: IBKR Client (MOST COMPLEX, HIGHEST RISK)
**Estimated Time**: 2-3 days
**Why Third**: Heart of the system, needs most testing

**Decision Point**: Choose `ib_async` vs raw `ibapi`
- ✅ **Recommended**: Use `ib_async` (cleaner async API)
- ⚠️ Alternative: Raw `ibapi` (more complex but official)

- **Task 2.1**: Implement `bot/ibkr/client.py` - Phase A (Connection)
  - [ ] Install `ib_async`: `pip install ib_async`
  - [ ] Basic connection/disconnection
  - [ ] Connection health check
  - [ ] Auto-reconnect logic
  - [ ] Error handling
  - [ ] Test with IB Gateway (paper mode)
  - **Deliverable**: Can connect to IBKR and stay connected

- **Task 2.2**: Implement `bot/ibkr/client.py` - Phase B (Market Data)
  - [ ] Subscribe to real-time bars (5-minute bars)
  - [ ] Bar data callback handling
  - [ ] Unsubscribe functionality
  - [ ] Test receiving live data
  - **Deliverable**: Can receive market data from MES

- **Task 2.3**: Implement `bot/ibkr/client.py` - Phase C (Orders)
  - [ ] Place market order
  - [ ] Place limit order
  - [ ] Cancel order
  - [ ] Order status tracking
  - [ ] Fill confirmation
  - [ ] Test order placement (paper trading)
  - **Deliverable**: Can place and monitor orders

- **Task 2.4**: Implement `bot/ibkr/client.py` - Phase D (Positions)
  - [ ] Get current positions
  - [ ] Get account summary
  - [ ] Flatten position (close specific)
  - [ ] Flatten all (emergency close)
  - [ ] Test position tracking
  - **Deliverable**: Can track and close positions

---

### Priority 4: Signal Generation (TRADING LOGIC)
**Estimated Time**: 1 day
**Why Fourth**: Needs market data from IBKR client

- **Task 3.1**: Implement `bot/core/signals.py`
  - [ ] Define `Signal` dataclass (LONG/SHORT/EXIT/NONE)
  - [ ] Create `SignalGenerator` class
  - [ ] Initialize Rust Z-Score engine
  - [ ] `on_bar()` method to process incoming bars
  - [ ] Entry logic: Z-Score >= ±2.0
  - [ ] Exit logic: Z-Score returns to ±0.5
  - [ ] Volume filter (min_volume threshold)
  - [ ] Track position state
  - [ ] Write 15+ unit tests with mock data
  - **Deliverable**: Generates correct signals from bar data

---

### Priority 5: Risk Management (SAFETY CRITICAL)
**Estimated Time**: 1 day
**Why Fifth**: Must have before allowing real orders

- **Task 3.2**: Implement `bot/risk/circuit_breaker.py`
  - [ ] Create `CircuitBreaker` class
  - [ ] Track daily P&L
  - [ ] Track consecutive losses
  - [ ] Track trade count for the day
  - [ ] `check_can_trade()` method with all checks:
    - [ ] Daily loss limit check
    - [ ] Consecutive loss check (with pause mechanism)
    - [ ] Max trades per day check
    - [ ] Pause timeout check
  - [ ] `record_trade()` to update state
  - [ ] `reset_daily()` for daily reset
  - [ ] Position duration checking (using Rust Risk Calculator)
  - [ ] Write 10+ unit tests
  - **Deliverable**: Enforces all risk limits correctly

---

### Priority 6: Database Persistence (OPTIONAL FOR MVP)
**Estimated Time**: 4-6 hours
**Why Sixth**: Useful but not blocking

- **Task 4.1**: Implement `bot/persistence/database.py`
  - [ ] Define SQLAlchemy models (Trade, Signal, Event)
  - [ ] `init_db()` to create tables
  - [ ] `log_trade()` to insert trades
  - [ ] `log_signal()` to insert signals
  - [ ] `log_event()` to insert events
  - [ ] `get_trades()` query method
  - [ ] `get_daily_pnl()` aggregation
  - [ ] Write 8+ unit tests
  - **Deliverable**: Logs all activity to SQLite
  - **MVP Alternative**: Can skip and use file logging initially

---

### Priority 7: Trading Engine (ORCHESTRATION)
**Estimated Time**: 1-2 days
**Why Seventh**: Ties everything together

- **Task 4.2**: Implement `bot/core/engine.py`
  - [ ] Create `TradingEngine` class
  - [ ] Initialize all components:
    - [ ] Load config
    - [ ] Create IBKR client
    - [ ] Create signal generator
    - [ ] Create circuit breaker
    - [ ] Create Telegram manager
    - [ ] Create database manager (optional)
  - [ ] Implement state machine:
    - [ ] IDLE → ENTERING_LONG → LONG → EXITING_LONG → IDLE
    - [ ] IDLE → ENTERING_SHORT → SHORT → EXITING_SHORT → IDLE
  - [ ] `start()` method:
    - [ ] Connect to IBKR
    - [ ] Start Telegram
    - [ ] Subscribe to market data
    - [ ] Reconcile positions on startup
    - [ ] Main event loop
  - [ ] `on_bar()` callback:
    - [ ] Generate signal
    - [ ] Check circuit breaker
    - [ ] Check trading hours
    - [ ] Execute orders
  - [ ] `process_signal()` method:
    - [ ] Route to correct handler (enter/exit)
  - [ ] Order execution methods:
    - [ ] `enter_long()`
    - [ ] `enter_short()`
    - [ ] `exit_long()`
    - [ ] `exit_short()`
    - [ ] `force_exit()` (duration exceeded)
  - [ ] `shutdown()` method:
    - [ ] Flatten all positions
    - [ ] Disconnect IBKR
    - [ ] Stop Telegram
    - [ ] Send shutdown alert
  - [ ] Write integration tests
  - **Deliverable**: Complete trading loop working

---

### Priority 8: Main Entry Point (BOOTSTRAP)
**Estimated Time**: 2-3 hours
**Why Eighth**: Simple wrapper around engine

- **Task 4.3**: Implement `bot/main.py`
  - [ ] Argument parsing (config file path, --dry-run flag)
  - [ ] Logging setup (file + console)
  - [ ] Load configuration
  - [ ] Signal handlers (SIGTERM, SIGINT)
  - [ ] Create TradingEngine
  - [ ] Exception handling
  - [ ] Graceful shutdown
  - [ ] Test startup/shutdown
  - **Deliverable**: Bot can be started from command line

---

### Priority 9: Testing & Validation (CRITICAL BEFORE LIVE)
**Estimated Time**: 1-2 weeks
**Why Last**: Need working system first

- **Task 5.1**: Unit Tests
  - [ ] bot/config.py (15 tests)
  - [ ] bot/core/signals.py (20 tests)
  - [ ] bot/risk/circuit_breaker.py (15 tests)
  - [ ] bot/persistence/database.py (10 tests, optional)
  - [ ] Achieve >90% code coverage

- **Task 5.2**: Integration Tests
  - [ ] IBKR client connection/reconnection
  - [ ] Market data subscription
  - [ ] Order placement and fills
  - [ ] Position tracking
  - [ ] Trading engine with simulated signals
  - [ ] Circuit breaker triggers
  - [ ] Telegram delivery

- **Task 5.3**: System Tests (48+ Hour Dry Run)
  - [ ] Deploy to test environment
  - [ ] Enable DEBUG logging
  - [ ] Monitor continuously for 48+ hours
  - [ ] Test crash recovery (kill and restart)
  - [ ] Test IB Gateway disconnect/reconnect
  - [ ] Check for memory leaks
  - [ ] Review all logs for errors

- **Task 5.4**: Edge Case Testing
  - [ ] Market close during open position
  - [ ] Order rejection scenarios
  - [ ] Extreme Z-Score values
  - [ ] Rapid price movements
  - [ ] Connection loss during order execution

---

## 📊 Estimated Timeline (Aggressive)

| Phase | Tasks | Estimated Time | Dependencies |
|-------|-------|----------------|--------------|
| **Phase 1** | Config + Contracts | 6-9 hours | None |
| **Phase 2** | IBKR Client | 2-3 days | Phase 1 |
| **Phase 3** | Signals + Risk | 2 days | Phase 2 |
| **Phase 4** | Engine + Main | 2-3 days | Phase 3 |
| **Phase 5** | Testing | 1-2 weeks | Phase 4 |
| **TOTAL** | **3-4 weeks** | | |

**Realistic Timeline**: 4-6 weeks (accounting for debugging, unexpected issues)

---

## 🎯 MVP Definition (Minimum Viable Product)

To reach **paper trading readiness**, you need:

### Must Have:
- ✅ Configuration parser
- ✅ IBKR client (all 4 phases)
- ✅ Signal generator
- ✅ Circuit breaker
- ✅ Trading engine
- ✅ Main entry point
- ✅ Unit tests (>80% coverage)
- ✅ 48+ hour dry run

### Nice to Have (can defer):
- Database persistence (use file logging initially)
- Web dashboard (Phase 6 - post-MVP)
- Backtest engine (Phase 7 - post-MVP)
- Telegram command handler (/status, /flatten)
- Multiple timeframes
- Trend filter

---

## 🚧 Risk Mitigation Strategies

### 1. IBKR Client Complexity
**Risk**: Most complex module, highest chance of issues
**Mitigation**:
- Use `ib_async` library (not raw `ibapi`)
- Build in phases (connection → data → orders → positions)
- Test each phase thoroughly before moving on
- Have fallback: manual flatten in TWS if bot fails

### 2. Configuration Errors
**Risk**: Invalid config causes runtime failures
**Mitigation**:
- Comprehensive validation in config.py
- Fail fast on startup, not during trading
- Provide clear error messages

### 3. State Management
**Risk**: Bot loses track of positions after crash
**Mitigation**:
- Reconcile positions on startup from IBKR
- Default action: flatten unknown positions
- Log all state changes

### 4. Testing Debt
**Risk**: Skip testing to move faster, bugs pile up
**Mitigation**:
- Write tests as you code, not after
- Aim for 80%+ coverage before moving to next phase
- Integration tests are non-negotiable

---

## 📋 Daily Progress Tracking

Use this checklist to track daily progress:

**Day 1-2**: Phase 1 (Config + Contracts)
- [ ] bot/config.py implemented
- [ ] bot/ibkr/contracts.py implemented
- [ ] Tests written and passing
- [ ] Can load config successfully

**Day 3-5**: Phase 2 (IBKR Client)
- [ ] Connection working
- [ ] Market data subscription working
- [ ] Order placement working
- [ ] Position tracking working
- [ ] Integration tests passing

**Day 6-7**: Phase 3 (Signals + Risk)
- [ ] Signal generator implemented
- [ ] Circuit breaker implemented
- [ ] Unit tests passing

**Day 8-10**: Phase 4 (Engine + Main)
- [ ] Trading engine implemented
- [ ] Main entry point implemented
- [ ] End-to-end test successful

**Week 2-3**: Phase 5 (Testing)
- [ ] All unit tests passing (>80% coverage)
- [ ] Integration tests passing
- [ ] 48+ hour dry run completed
- [ ] Edge cases tested

**Week 4**: Refinement & Documentation
- [ ] Bug fixes from testing
- [ ] Code review and cleanup
- [ ] Documentation updated
- [ ] Deployment checklist verified

---

## 🔍 Definition of Done (Each Task)

A task is only "done" when:
- [ ] Code written and committed
- [ ] Unit tests written and passing
- [ ] Integration tests passing (if applicable)
- [ ] Code reviewed (self or peer)
- [ ] Documentation updated
- [ ] No TODOs or FIXMEs left in code
- [ ] Pushed to GitHub

---

## 🚀 Quick Start Command

Once all phases complete:

```bash
# Activate environment
source venv/bin/activate

# Run bot
python -m bot.main config/config.yaml

# Run with dry-run (no real orders)
python -m bot.main config/config.yaml --dry-run
```

---

## 🛟 Emergency Procedures (Must Test Before Live)

Before paper trading, test ALL of these:

1. **Manual Flatten via Telegram**: `/flatten`
2. **Kill and Restart**: `kill -9 <pid>` then restart
3. **IB Gateway Disconnect**: Stop Gateway, verify reconnect
4. **Circuit Breaker**: Manually trigger loss limit
5. **Position Duration**: Let position exceed max duration
6. **Daily Reset**: Verify reset at market open

---

## 📚 Key Implementation References

- **IBKR API**: https://interactivebrokers.github.io/tws-api/
- **ib_async**: https://github.com/ib-api-reloaded/ib_async
- **MES Contract**: https://www.cmegroup.com/markets/equities/sp/micro-e-mini-sandp-500.html
- **Z-Score Strategy**: Already implemented in Rust (`rust/src/zscore.rs`)

---

**Remember**: Quality over speed. A bug in production can cost real money. Test thoroughly at every stage.
