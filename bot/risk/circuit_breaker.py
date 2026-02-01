"""
Circuit Breaker System

Enforces risk limits and halts trading when conditions are breached.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Callable
from dataclasses import dataclass, field

from ..core.engine import EngineState, DailyStats

logger = logging.getLogger(__name__)


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration"""
    max_daily_loss: float = 500.0
    max_consecutive_losses: int = 3
    max_position_duration_hours: float = 2.0
    max_drawdown: float = 1000.0  # Maximum peak-to-trough drawdown
    cooldown_minutes: int = 30  # Minimum pause time after trigger


@dataclass
class CircuitBreakerState:
    """Current circuit breaker state"""
    triggered: bool = False
    trigger_time: Optional[datetime] = None
    trigger_reason: str = ""
    peak_equity: float = 0.0
    current_equity: float = 0.0


class CircuitBreaker:
    """Circuit breaker for risk management"""

    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.state = CircuitBreakerState()
        self._callback: Optional[Callable] = None
        self._monitor_task: Optional[asyncio.Task] = None

    def set_trigger_callback(self, callback: Callable[[str], None]):
        """
        Set callback function to call when circuit breaker triggers.

        Args:
            callback: Function that receives trigger reason
        """
        self._callback = callback
        logger.info("Circuit breaker callback registered")

    def reset(self):
        """Reset circuit breaker (manually or after cooldown)"""
        logger.info("Circuit breaker reset")
        self.state = CircuitBreakerState(
            current_equity=self.state.current_equity,
            peak_equity=self.state.current_equity,
        )

    def check_daily_loss_limit(self, stats: DailyStats) -> bool:
        """
        Check if daily loss limit is breached.

        Args:
            stats: Daily trading statistics

        Returns:
            True if limit breached, False otherwise
        """
        if stats.realized_pnl <= -self.config.max_daily_loss:
            reason = f"Daily loss limit reached (${abs(stats.realized_pnl):.2f} < -${self.config.max_daily_loss:.2f})"
            logger.error(reason)
            self._trigger(reason)
            return True

        return False

    def check_consecutive_losses(self, stats: DailyStats) -> bool:
        """
        Check if too many consecutive losses.

        Args:
            stats: Daily trading statistics

        Returns:
            True if limit breached, False otherwise
        """
        if stats.consecutive_losses >= self.config.max_consecutive_losses:
            reason = f"Too many consecutive losses ({stats.consecutive_losses} >= {self.config.max_consecutive_losses})"
            logger.error(reason)
            self._trigger(reason)
            return True

        return False

    def check_drawdown(self, equity: float) -> bool:
        """
        Check if drawdown limit is breached.

        Args:
            equity: Current account equity

        Returns:
            True if limit breached, False otherwise
        """
        self.state.current_equity = equity

        # Track peak equity
        if equity > self.state.peak_equity:
            self.state.peak_equity = equity

        # Calculate drawdown
        drawdown = self.state.peak_equity - equity

        if drawdown >= self.config.max_drawdown:
            reason = f"Drawdown limit reached (${drawdown:.2f} >= ${self.config.max_drawdown:.2f})"
            logger.error(reason)
            self._trigger(reason)
            return True

        return False

    def check_position_duration(
        self,
        entry_time: datetime,
        current_time: Optional[datetime] = None,
    ) -> bool:
        """
        Check if position held too long.

        Args:
            entry_time: When the position was entered
            current_time: Current time (defaults to now)

        Returns:
            True if limit breached, False otherwise
        """
        if current_time is None:
            current_time = datetime.utcnow()

        duration = current_time - entry_time
        max_duration = timedelta(hours=self.config.max_position_duration_hours)

        if duration >= max_duration:
            reason = f"Position held too long ({duration} >= {max_duration})"
            logger.warning(reason)
            self._trigger(reason)
            return True

        return False

    def _trigger(self, reason: str):
        """Trigger the circuit breaker"""
        if self.state.triggered:
            logger.warning("Circuit breaker already triggered")
            return

        logger.error(f"⚠️ CIRCUIT BREAKER TRIGGERED: {reason}")

        self.state.triggered = True
        self.state.trigger_time = datetime.utcnow()
        self.state.trigger_reason = reason

        # Call callback if registered
        if self._callback:
            self._callback(reason)

    def can_trade(self) -> bool:
        """
        Check if trading is allowed.

        Returns:
            True if allowed, False if circuit breaker is active
        """
        if not self.state.triggered:
            return True

        # Check if cooldown has passed
        if self.state.trigger_time:
            elapsed = datetime.utcnow() - self.state.trigger_time
            cooldown = timedelta(minutes=self.config.cooldown_minutes)

            if elapsed >= cooldown:
                logger.info("Circuit breaker cooldown expired, allowing trading")
                self.reset()
                return True

        return False

    def get_status(self) -> dict:
        """Get current circuit breaker status"""
        status = {
            "triggered": self.state.triggered,
            "trigger_reason": self.state.trigger_reason,
            "can_trade": self.can_trade(),
        }

        if self.state.trigger_time:
            elapsed = datetime.utcnow() - self.state.trigger_time
            cooldown = timedelta(minutes=self.config.cooldown_minutes)
            remaining = max(timedelta(0), cooldown - elapsed)
            status["cooldown_remaining"] = str(remaining)

        status["drawdown"] = self.state.peak_equity - self.state.current_equity
        status["peak_equity"] = self.state.peak_equity
        status["current_equity"] = self.state.current_equity

        return status


def test_circuit_breaker():
    """Test circuit breaker functionality"""
    import asyncio

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
    stats = DailyStats(realized_pnl=-150.0)
    assert cb.check_daily_loss_limit(stats)
    assert not cb.can_trade()
    print("✅ Daily loss limit test passed")

    # Test 2: Consecutive losses
    cb.reset()
    print("\n--- Test 2: Consecutive Losses ---")
    stats = DailyStats(consecutive_losses=3)
    assert cb.check_consecutive_losses(stats)
    assert not cb.can_trade()
    print("✅ Consecutive losses test passed")

    # Test 3: Drawdown
    cb.reset()
    print("\n--- Test 3: Drawdown ---")
    assert cb.check_drawdown(10000.0)  # Set peak
    assert not cb.check_drawdown(9500.0)  # Within limit
    assert cb.check_drawdown(8900.0)  # Over limit (1000 drawdown)
    assert not cb.can_trade()
    print("✅ Drawdown test passed")

    # Test 4: Cooldown
    cb.reset()
    print("\n--- Test 4: Cooldown ---")
    cb.set_trigger_callback(lambda r: triggered_reasons.append(r))
    cb._trigger("Manual trigger")
    assert not cb.can_trade()
    print(f"   Cooldown remaining: {cb.get_status()['cooldown_remaining']}")

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


if __name__ == "__main__":
    test_circuit_breaker()
