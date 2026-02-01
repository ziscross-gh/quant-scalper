#!/usr/bin/env python3
"""
Standalone test for Circuit Breaker (avoiding circular imports)
"""
import sys
sys.path.insert(0, '.')

from datetime import datetime, timedelta

# Define minimal mocks to avoid importing core.engine
class MockDailyStats:
    def __init__(self, realized_pnl=0.0, consecutive_losses=0):
        self.realized_pnl = realized_pnl
        self.consecutive_losses = consecutive_losses

# Import only circuit breaker module
from bot.risk.circuit_breaker import CircuitBreaker, CircuitBreakerConfig

print("Testing Circuit Breaker")
print("=" * 50)

config = CircuitBreakerConfig(
    max_daily_loss=100.0,
    max_consecutive_losses=2,
)

cb = CircuitBreaker(config)

# Track triggers
triggered_reasons = []

def on_trigger(reason):
    triggered_reasons.append(reason)
    print(f"🚨 Circuit breaker triggered: {reason}")

cb.set_trigger_callback(on_trigger)

# Test 1: Daily loss limit
print("\n--- Test 1: Daily Loss Limit ---")
stats = MockDailyStats(realized_pnl=-150.0)
assert cb.check_daily_loss_limit(stats)
assert not cb.can_trade()
print("✅ Daily loss limit test passed")

# Test 2: Consecutive losses
cb.reset()
print("\n--- Test 2: Consecutive Losses ---")
stats = MockDailyStats(consecutive_losses=3)
assert cb.check_consecutive_losses(stats)
assert not cb.can_trade()
print("✅ Consecutive losses test passed")

# Test 3: Drawdown
cb.reset()
print("\n--- Test 3: Drawdown ---")
cb.check_drawdown(10000.0)  # Set peak (returns False, no drawdown)
assert not cb.check_drawdown(9500.0)  # Within limit
assert cb.check_drawdown(8900.0)  # Over limit (1000 drawdown)
assert not cb.can_trade()
print("✅ Drawdown test passed")

# Test 4: Cooldown
cb.reset()
print("\n--- Test 4: Cooldown ---")
cb._trigger("Manual trigger")
assert not cb.can_trade()
status = cb.get_status()
print(f"   Cooldown remaining: {status['cooldown_remaining']}")

# Manually reset after cooldown
cb.state.trigger_time = datetime.utcnow() - timedelta(minutes=31)
assert cb.can_trade()
print("✅ Cooldown test passed")

# Test 5: Position duration
cb.reset()
print("\n--- Test 5: Position Duration ---")
entry = datetime.utcnow() - timedelta(hours=3)
assert cb.check_position_duration(entry)
print("✅ Position duration test passed")

print("\n" + "=" * 50)
print("✅ All circuit breaker tests passed!")
print(f"   Total triggers: {len(triggered_reasons)}")
