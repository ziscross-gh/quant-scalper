# Task 5.5: Circuit Breaker Testing

**Owner:** Sofia (squad-sofia)
**Status:** ⏸️ WAITING FOR DEPENDENCIES
**Priority:** 🔥 CRITICAL
**Deadline:** After Task 5.4 completes
**Assigned:** February 3, 2026 10:35 AM GMT+8

---

## 🎯 Objective

Verify all circuit breaker mechanisms trigger correctly and protect the bot from excessive losses.

---

## 📋 Circuit Breaker Configuration

From `config/config.yaml`:

```yaml
risk:
  max_position_size: 2
  stop_loss_dollars: 200
  take_profit_dollars: 300
  max_daily_loss: 500           # Hard daily loss limit
  max_consecutive_losses: 3     # Pause after 3 losses
  max_position_duration_hours: 2.0  # Force close after 2 hours
```

---

## ⏸️ Dependencies

**This task depends on:**
- ✅ Task 5.1: IBKR Gateway Testing (Kai)
- ✅ Task 5.2: Market Data Testing (Kai)
- ✅ Task 5.3: Order Execution Testing (Kai)
- ✅ Task 5.4: Position Tracking Testing (Kai + Sofia)

**Wait for Kai to complete Task 5.4 before starting.**

---

## ✅ Checklist

- [ ] Test daily P&L limit trigger ($500)
- [ ] Test consecutive loss pause (3 trades)
- [ ] Test max position duration (2 hours)
- [ ] Test circuit breaker state tracking
- [ ] Verify pause timeout mechanism
- [ ] Test daily reset functionality

---

## 🚀 Steps to Execute

### Step 1: Prepare Test Environment

```bash
cd /Users/ziscross/.openclaw/workspace/quant-scalper
source venv/bin/activate

# Ensure database is clean
rm -f data/circuit_breaker.db

# Set up test configuration
cp config/config.yaml config/config.yaml.backup
```

---

### Step 2: Test Daily P&L Limit

Create test script:

```bash
cat > test_daily_loss_limit.py << 'EOF'
#!/usr/bin/env python3
"""Test daily P&L limit circuit breaker"""

from bot.risk.circuit_breaker import CircuitBreaker
from bot.config import Config

async def test_daily_loss_limit():
    """Test that daily loss limit triggers correctly"""

    # Load config
    config = Config.load('config/config.yaml')

    # Create circuit breaker
    cb = CircuitBreaker(config)

    print("Testing daily P&L limit...")
    print(f"Max daily loss: ${config.risk.max_daily_loss}")

    # Record a series of losses to hit the limit
    losses = [-150, -150, -200]  # Total: -$500
    for i, loss in enumerate(losses, 1):
        cb.record_trade(loss)
        can_trade, reason = cb.check_can_trade()
        print(f"After trade {i} (${loss}): P&L=${cb.daily_pnl:.2f}, Can trade={can_trade}")
        if not can_trade:
            print(f"✅ Circuit breaker triggered: {reason}")
            break
    else:
        print("❌ Circuit breaker did not trigger!")

    # Verify circuit breaker is now blocking
    can_trade, reason = cb.check_can_trade()
    if not can_trade and "daily loss" in reason.lower():
        print("✅ Circuit breaker is correctly blocking trading")
    else:
        print(f"❌ Circuit breaker not blocking properly: {reason}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_daily_loss_limit())
EOF

python test_daily_loss_limit.py
```

**Expected Output:**
```
Testing daily P&L limit...
Max daily loss: $500
After trade 1 ($-150): P&L=$-150.00, Can trade=True
After trade 2 ($-150): P&L=$-300.00, Can trade=True
After trade 3 ($-200): P&L=$-500.00, Can trade=False
✅ Circuit breaker triggered: Daily loss limit: $500.00
✅ Circuit breaker is correctly blocking trading
```

---

### Step 3: Test Consecutive Loss Pause

```bash
cat > test_consecutive_losses.py << 'EOF'
#!/usr/bin/env python3
"""Test consecutive loss pause circuit breaker"""

from bot.risk.circuit_breaker import CircuitBreaker
from bot.config import Config
import asyncio
from datetime import datetime, timezone, timedelta

async def test_consecutive_losses():
    """Test that consecutive losses trigger pause"""

    config = Config.load('config/config.yaml')
    cb = CircuitBreaker(config)

    print("Testing consecutive loss pause...")
    print(f"Max consecutive losses: {config.risk.max_consecutive_losses}")

    # Record 3 consecutive losses
    for i in range(3):
        cb.record_trade(-100)
        can_trade, reason = cb.check_can_trade()
        print(f"Loss #{i+1}: Consecutive losses={cb.consecutive_losses}, Can trade={can_trade}")

    # Check if pause was triggered
    can_trade, reason = cb.check_can_trade()
    if not can_trade and "consecutive" in reason.lower():
        print(f"✅ Pause triggered: {reason}")
        print(f"Pause until: {cb.paused_until}")

        # Test that pause expires
        original_pause = cb.paused_until
        # Simulate time passing
        cb.paused_until = datetime.now(timezone.utc) - timedelta(seconds=1)

        can_trade, reason = cb.check_can_trade()
        if can_trade:
            print("✅ Pause expired, trading allowed again")
        else:
            print(f"❌ Pause did not expire: {reason}")
    else:
        print(f"❌ Consecutive loss pause not triggered: {reason}")

if __name__ == "__main__":
    asyncio.run(test_consecutive_losses())
EOF

python test_consecutive_losses.py
```

**Expected Output:**
```
Testing consecutive loss pause...
Max consecutive losses: 3
Loss #1: Consecutive losses=1, Can trade=True
Loss #2: Consecutive losses=2, Can trade=True
Loss #3: Consecutive losses=3, Can trade=False
✅ Pause triggered: Consecutive losses limit exceeded
Pause until: 2026-02-03 11:05:00+00:00
✅ Pause expired, trading allowed again
```

---

### Step 4: Test Position Duration Limit

```bash
cat > test_position_duration.py << 'EOF'
#!/usr/bin/env python3
"""Test position duration limit circuit breaker"""

from bot.risk.circuit_breaker import CircuitBreaker
from bot.config import Config
import asyncio
from datetime import datetime, timezone, timedelta

async def test_position_duration():
    """Test that position duration limit triggers"""

    config = Config.load('config/config.yaml')
    cb = CircuitBreaker(config)

    print("Testing position duration limit...")
    print(f"Max position duration: {config.risk.max_position_duration_hours} hours")

    # Simulate position entry
    cb.position_entry_time = datetime.now(timezone.utc) - timedelta(hours=2.5)

    # Check if duration exceeded
    duration_exceeded = cb.check_position_duration()
    if duration_exceeded:
        print(f"✅ Position duration exceeded, should force exit")
    else:
        print(f"❌ Position duration check failed")

    # Test with fresh position
    cb.position_entry_time = datetime.now(timezone.utc) - timedelta(minutes=30)
    duration_exceeded = cb.check_position_duration()
    if not duration_exceeded:
        print(f"✅ Fresh position, duration not exceeded")
    else:
        print(f"❌ Position duration check incorrect for fresh position")

if __name__ == "__main__":
    asyncio.run(test_position_duration())
EOF

python test_position_duration.py
```

**Expected Output:**
```
Testing position duration limit...
Max position duration: 2.0 hours
✅ Position duration exceeded, should force exit
✅ Fresh position, duration not exceeded
```

---

### Step 5: Test Daily Reset

```bash
cat > test_daily_reset.py << 'EOF'
#!/usr/bin/env python3
"""Test daily reset functionality"""

from bot.risk.circuit_breaker import CircuitBreaker
from bot.config import Config

async def test_daily_reset():
    """Test that daily counters reset correctly"""

    config = Config.load('config/config.yaml')
    cb = CircuitBreaker(config)

    print("Testing daily reset...")

    # Record some losses
    cb.record_trade(-100)
    cb.record_trade(-50)
    print(f"Before reset: P&L=${cb.daily_pnl}, Losses={cb.consecutive_losses}, Trades={cb.trade_count_today}")

    # Perform daily reset
    cb.reset_daily()
    print(f"After reset: P&L=${cb.daily_pnl}, Losses={cb.consecutive_losses}, Trades={cb.trade_count_today}")

    # Verify all counters are zero
    if cb.daily_pnl == 0.0 and cb.consecutive_losses == 0 and cb.trade_count_today == 0:
        print("✅ All counters reset correctly")
    else:
        print("❌ Daily reset failed")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_daily_reset())
EOF

python test_daily_reset.py
```

**Expected Output:**
```
Testing daily reset...
Before reset: P&L=$-150.00, Losses=2, Trades=2
After reset: P&L=$0.00, Losses=0, Trades=0
✅ All counters reset correctly
```

---

## 📊 Success Criteria

- [ ] Daily P&L limit triggers at $500 loss
- [ ] Consecutive loss pause triggers after 3 losses
- [ ] Pause expires after timeout
- [ ] Position duration limit triggers after 2 hours
- [ ] Daily reset clears all counters
- [ ] All circuit breakers block trading correctly
- [ ] No false positives (blocks when it shouldn't)

---

## 📝 Report Template

```markdown
## Results

**Status:** ✅ PASSED / ❌ FAILED / ⚠️ PARTIAL

### Daily P&L Limit
- ✅ / ❌ Triggered at correct threshold ($500)
- ✅ / ❌ Blocked trading correctly
- ✅ / ❌ Reset after daily reset

### Consecutive Loss Pause
- ✅ / ❌ Triggered after 3 losses
- ✅ / ❌ Paused for correct duration
- ✅ / ❌ Expired after timeout
- ✅ / ❌ Reset on winning trade

### Position Duration Limit
- ✅ / ❌ Detected 2+ hour positions
- ✅ / ❌ Did not trigger for fresh positions

### Daily Reset
- ✅ / ❌ All counters reset to zero
- ✅ / ❌ Circuit breakers cleared

**Errors/Issues:**
- [List any errors]

**Logs:**
[Attach relevant log excerpts]

**Recommendations:**
[Any issues found and how to fix them]
```

---

## 🆘 Troubleshooting

### Circuit breaker not triggering
**Cause:** Thresholds may not be reached

**Solution:**
1. Verify P&L is actually being calculated
2. Check trade recording is working
3. Review circuit breaker logic in code

### Circuit breaker triggering incorrectly
**Cause:** False positive from conditions

**Solution:**
1. Review threshold values in config
2. Check for rounding errors in P&L calculation
3. Verify state transitions are correct

---

## 📚 References

- Circuit Breaker Code: `/Users/ziscross/.openclaw/workspace/quant-scalper/bot/risk/circuit_breaker.py`
- Config File: `/Users/ziscross/.openclaw/workspace/quant-scalper/config/config.yaml`

---

**Once complete, report to Marcus and proceed to Task 5.6!**
