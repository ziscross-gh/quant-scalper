# Opus Analysis - Quant Scalping Bot

**Analyzed:** 2026-01-31 16:43 GMT+8

---

## 🚨 Critical Issues Found

### 1. Numerical Stability Bug in Z-Score Engine (CRITICAL)

**Problem:** The Rust Z-Score engine claims to use "Welford's algorithm" but actually uses the naive formula that's numerically unstable for large values.

**Impact:** With MES prices around 5000-6000, this will accumulate floating-point errors over time, leading to incorrect Z-Scores and bad trading decisions.

**Location:** `rust/src/zscore.rs` lines 99-100, 160

**Fix Required:** Implement proper Welford's algorithm or use numerically stable variance calculation.

---

### 2. Most Core Modules Are Missing

**Problem:** Despite documentation saying "Phase 1-4 Complete", these critical files don't exist:
- `bot/main.py` — Entry point
- `bot/config.py` — Configuration loader
- `bot/ibkr/client.py` — IBKR integration
- `bot/core/engine.py` — Trading engine
- `bot/core/signals.py` — Signal generation
- `bot/risk/circuit_breaker.py` — Risk management
- `bot/persistence/database.py` — Database

**Current State:** Only Rust math engine, Telegram alerts, and utilities exist.

---

### 3. Trading Hours Logic Bug

**Problem:** `is_trading_allowed()` uses stock market hours (9:30 AM - 4:00 PM) instead of futures hours (nearly 24-hour).

**Impact:** MES trades almost 24/7 but the bot would only trade 6.5 hours/day, missing 75% of opportunities.

**Location:** `bot/utils/timezone.py` line 216

**Fix Required:** Update to use CME futures trading hours.

---

### 4. Strategy Is Not Actually "Scalping"

**Problem:**
- $200 stop loss = 40 MES points
- $300 take profit = 60 MES points

**Reality:** These are swing trading levels, not scalping (which uses 2-10 point targets).

**Recommendation:** Either rename the project to "Swing Trader" or adjust parameters to true scalping levels ($20-50 targets).

---

## 📋 Other Important Issues

- **No tests exist** — `tests` directory is empty
- **Holiday calendar outdated** — Only has 2025 data (it's 2026)
- **Telegram no retry logic** — Messages lost on failure
- **No position timestamps** — Can't enforce 2-hour max duration rule
- **Documentation redundancy** — Same info repeated across 6 files

---

## ✅ What's Actually Working

- ✅ Rust Z-Score calculation (but needs stability fix)
- ✅ Rust Risk Calculator
- ✅ Telegram alert sender (send-only, no commands)
- ✅ Timezone utilities (with bugs noted above)
- ✅ Project structure and infrastructure

---

## 🎯 Prioritized Action Plan

### Immediate (Fix Existing Code) - 1-2 days

1. **Fix Z-Score numerical stability** — Implement proper Welford's algorithm
2. **Fix trading hours logic** — Use CME futures hours (near 24/7)
3. **Update holiday calendar** — Add 2026 holidays
4. **Fix Telegram HTML injection** — Sanitize user input in messages

### Core Implementation - 1-2 weeks

1. Build `bot/config.py` — Configuration loader with validation
2. Build `bot/ibkr/client.py` — IBKR integration (consider `ib_async` instead of raw `ibapi`)
3. Build `bot/core/signals.py` — Signal generation logic
4. Build `bot/risk/circuit_breaker.py` — Risk management system
5. Build `bot/core/engine.py` — Main trading engine
6. Build `bot/main.py` — Entry point and CLI

### Testing - 1-2 weeks

1. **Write unit tests** — None exist currently
2. **Integration tests** — Test with IBKR paper account
3. **48+ hour dry run** — Continuous operation before paper trading

### Paper Trading - 3+ months

Before even considering live trading.

---

## 💡 Key Recommendations

1. **Use `ib_async` instead of raw `ibapi`** — Cleaner async integration, better error handling
2. **Add trend filter** — Prevent mean reversion in trending markets (e.g., ADX filter)
3. **Realistic expectations** — 4-6 weeks to paper trading readiness, not 1-2 weeks
4. **Add missing safeguards** — Max trades/day, margin checks, weekend flattening
5. **Define bar timeframe** — "20 bars" is meaningless without knowing if it's ticks, seconds, or minutes

---

## ⚠️ Reality Check

**The repo says:** "Phase 1-4 Complete"
**The reality:** Infrastructure is ready, but core trading logic doesn't exist

**What this means:**
- Good foundation (Rust engine, config system, docs)
- But 1-2 weeks of actual coding needed before any testing can begin
- Then 1-2 weeks of testing
- Then 3+ months of paper trading
- **Total: ~4-5 months before live trading is even possible**

This aligns with your Bazi — patience (Earth) and systematic approach (grounding) are required. Rushing to live trading = burnout + risk of "melting" your capital.
