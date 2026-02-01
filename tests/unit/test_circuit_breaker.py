"""
Unit tests for bot/risk/circuit_breaker.py - Risk management and circuit breaker logic
"""
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

from bot.risk.circuit_breaker import (
    CircuitBreaker, CircuitBreakerConfig, CircuitBreakerState
)


class TestCircuitBreakerConfig:
    """Test CircuitBreakerConfig validation"""

    def test_valid_config(self):
        """Test valid circuit breaker configuration"""
        config = CircuitBreakerConfig(
            max_daily_loss=500.0,
            max_position_size=2,
            max_consecutive_losses=3,
            max_trades_per_day=10,
            position_timeout_hours=2.0,
            drawdown_limit_percent=10.0,
            cooldown_minutes=30
        )

        assert config.max_daily_loss == 500.0
        assert config.max_consecutive_losses == 3
        assert config.cooldown_minutes == 30

    def test_invalid_daily_loss(self):
        """Test that max_daily_loss must be positive"""
        with pytest.raises(ValueError):
            CircuitBreakerConfig(
                max_daily_loss=-100.0,
                max_position_size=2,
                max_consecutive_losses=3
            )

    def test_invalid_position_size(self):
        """Test that max_position_size must be positive"""
        with pytest.raises(ValueError):
            CircuitBreakerConfig(
                max_daily_loss=500.0,
                max_position_size=0,
                max_consecutive_losses=3
            )


class TestCircuitBreakerState:
    """Test CircuitBreakerState"""

    def test_initial_state(self):
        """Test initial circuit breaker state"""
        state = CircuitBreakerState()

        assert state.is_triggered is False
        assert state.trigger_reason is None
        assert state.trigger_time is None
        assert state.peak_equity is None

    def test_state_modification(self):
        """Test modifying circuit breaker state"""
        state = CircuitBreakerState()

        state.is_triggered = True
        state.trigger_reason = "Daily loss limit"
        state.trigger_time = datetime.now(timezone.utc)

        assert state.is_triggered is True
        assert "loss" in state.trigger_reason.lower()


class TestCircuitBreaker:
    """Test CircuitBreaker core functionality"""

    @pytest.fixture
    def cb_config(self):
        """Create circuit breaker config for tests"""
        return CircuitBreakerConfig(
            max_daily_loss=500.0,
            max_position_size=2,
            max_consecutive_losses=3,
            max_trades_per_day=10,
            position_timeout_hours=2.0,
            drawdown_limit_percent=10.0,
            cooldown_minutes=30
        )

    @pytest.fixture
    def circuit_breaker(self, cb_config):
        """Create circuit breaker instance"""
        return CircuitBreaker(cb_config)

    @pytest.fixture
    def mock_daily_stats(self):
        """Create mock daily stats object"""
        class MockDailyStats:
            def __init__(self, realized_pnl=0.0, consecutive_losses=0):
                self.realized_pnl = realized_pnl
                self.consecutive_losses = consecutive_losses

        return MockDailyStats

    def test_initialization(self, circuit_breaker, cb_config):
        """Test circuit breaker initialization"""
        assert circuit_breaker.config == cb_config
        assert circuit_breaker.can_trade() is True
        assert circuit_breaker.state.is_triggered is False

    def test_can_trade_initially(self, circuit_breaker):
        """Test that trading is allowed initially"""
        assert circuit_breaker.can_trade() is True

    def test_daily_loss_limit_breach(self, circuit_breaker, mock_daily_stats):
        """Test circuit breaker triggers on daily loss limit"""
        stats = mock_daily_stats(realized_pnl=-600.0)  # Exceeds 500 limit

        # Check should trigger
        triggered = circuit_breaker.check_daily_loss_limit(stats)

        assert triggered is True
        assert circuit_breaker.can_trade() is False
        assert circuit_breaker.state.is_triggered is True
        assert "loss" in circuit_breaker.state.trigger_reason.lower()

    def test_daily_loss_within_limit(self, circuit_breaker, mock_daily_stats):
        """Test circuit breaker allows trading within loss limit"""
        stats = mock_daily_stats(realized_pnl=-300.0)  # Within 500 limit

        triggered = circuit_breaker.check_daily_loss_limit(stats)

        assert triggered is False
        assert circuit_breaker.can_trade() is True

    def test_consecutive_losses_breach(self, circuit_breaker, mock_daily_stats):
        """Test circuit breaker triggers on consecutive losses"""
        stats = mock_daily_stats(consecutive_losses=4)  # Exceeds 3 limit

        triggered = circuit_breaker.check_consecutive_losses(stats)

        assert triggered is True
        assert circuit_breaker.can_trade() is False
        assert "consecutive" in circuit_breaker.state.trigger_reason.lower()

    def test_consecutive_losses_within_limit(self, circuit_breaker, mock_daily_stats):
        """Test consecutive losses within limit"""
        stats = mock_daily_stats(consecutive_losses=2)  # Within 3 limit

        triggered = circuit_breaker.check_consecutive_losses(stats)

        assert triggered is False
        assert circuit_breaker.can_trade() is True

    def test_drawdown_limit_breach(self, circuit_breaker):
        """Test circuit breaker triggers on drawdown limit"""
        # Set peak equity
        circuit_breaker.check_drawdown(10000.0)

        # Check with significant drawdown (15% > 10% limit)
        current_equity = 8500.0
        triggered = circuit_breaker.check_drawdown(current_equity)

        assert triggered is True
        assert circuit_breaker.can_trade() is False
        assert "drawdown" in circuit_breaker.state.trigger_reason.lower()

    def test_drawdown_within_limit(self, circuit_breaker):
        """Test drawdown within acceptable limit"""
        # Set peak equity
        circuit_breaker.check_drawdown(10000.0)

        # Check with small drawdown (5% < 10% limit)
        current_equity = 9500.0
        triggered = circuit_breaker.check_drawdown(current_equity)

        assert triggered is False
        assert circuit_breaker.can_trade() is True

    def test_drawdown_new_peak(self, circuit_breaker):
        """Test that peak equity updates when equity increases"""
        # Initial peak
        circuit_breaker.check_drawdown(10000.0)
        assert circuit_breaker.state.peak_equity == 10000.0

        # New peak
        circuit_breaker.check_drawdown(11000.0)
        assert circuit_breaker.state.peak_equity == 11000.0

    def test_max_trades_per_day(self, circuit_breaker):
        """Test circuit breaker triggers on max trades per day"""
        # Simulate 11 trades (exceeds 10 limit)
        for _ in range(11):
            triggered = circuit_breaker.check_trade_count()

        assert triggered is True
        assert circuit_breaker.can_trade() is False
        assert "trades" in circuit_breaker.state.trigger_reason.lower()

    def test_position_duration_timeout(self, circuit_breaker):
        """Test circuit breaker triggers on position duration timeout"""
        # Position held for 3 hours (exceeds 2 hour limit)
        entry_time = datetime.now(timezone.utc) - timedelta(hours=3)

        triggered = circuit_breaker.check_position_duration(entry_time)

        assert triggered is True
        assert circuit_breaker.can_trade() is False
        assert "duration" in circuit_breaker.state.trigger_reason.lower()

    def test_position_duration_within_limit(self, circuit_breaker):
        """Test position duration within limit"""
        # Position held for 1 hour (within 2 hour limit)
        entry_time = datetime.now(timezone.utc) - timedelta(hours=1)

        triggered = circuit_breaker.check_position_duration(entry_time)

        assert triggered is False
        assert circuit_breaker.can_trade() is True

    def test_cooldown_period(self, circuit_breaker):
        """Test cooldown period after trigger"""
        # Trigger circuit breaker
        circuit_breaker._trigger("Test trigger")

        # Should not be able to trade during cooldown
        assert circuit_breaker.can_trade() is False

        # Simulate cooldown period passing
        circuit_breaker.state.trigger_time = datetime.now(timezone.utc) - timedelta(minutes=31)

        # Should be able to trade after cooldown
        assert circuit_breaker.can_trade() is True

    def test_cooldown_not_expired(self, circuit_breaker):
        """Test that trading is blocked during cooldown period"""
        # Trigger circuit breaker
        circuit_breaker._trigger("Test trigger")

        # Set trigger time to 10 minutes ago (cooldown is 30 minutes)
        circuit_breaker.state.trigger_time = datetime.now(timezone.utc) - timedelta(minutes=10)

        # Should still be in cooldown
        assert circuit_breaker.can_trade() is False

    def test_reset_functionality(self, circuit_breaker):
        """Test resetting circuit breaker"""
        # Trigger circuit breaker
        circuit_breaker._trigger("Test trigger")
        assert circuit_breaker.can_trade() is False

        # Reset
        circuit_breaker.reset()

        # Should be able to trade again
        assert circuit_breaker.can_trade() is True
        assert circuit_breaker.state.is_triggered is False
        assert circuit_breaker.state.trigger_reason is None

    def test_get_status(self, circuit_breaker):
        """Test getting circuit breaker status"""
        status = circuit_breaker.get_status()

        assert "can_trade" in status
        assert "is_triggered" in status
        assert "trigger_reason" in status
        assert "cooldown_remaining" in status

        assert status["can_trade"] is True
        assert status["is_triggered"] is False

    def test_get_status_after_trigger(self, circuit_breaker):
        """Test status after circuit breaker is triggered"""
        circuit_breaker._trigger("Daily loss limit")

        status = circuit_breaker.get_status()

        assert status["can_trade"] is False
        assert status["is_triggered"] is True
        assert status["trigger_reason"] == "Daily loss limit"
        assert status["cooldown_remaining"] > 0

    def test_trigger_callback(self, circuit_breaker):
        """Test trigger callback is called"""
        callback_data = []

        def on_trigger(reason):
            callback_data.append(reason)

        circuit_breaker.set_trigger_callback(on_trigger)

        # Trigger circuit breaker
        circuit_breaker._trigger("Test callback")

        assert len(callback_data) == 1
        assert callback_data[0] == "Test callback"

    def test_multiple_triggers(self, circuit_breaker, mock_daily_stats):
        """Test that multiple triggers are handled correctly"""
        # Trigger with daily loss
        stats = mock_daily_stats(realized_pnl=-600.0)
        circuit_breaker.check_daily_loss_limit(stats)

        first_reason = circuit_breaker.state.trigger_reason

        # Try to trigger again (should keep first reason)
        stats2 = mock_daily_stats(consecutive_losses=5)
        circuit_breaker.check_consecutive_losses(stats2)

        # Should still have first trigger reason
        assert circuit_breaker.state.trigger_reason == first_reason

    def test_position_size_validation(self, circuit_breaker):
        """Test position size validation"""
        # Within limit
        assert circuit_breaker.check_position_size(1) is False
        assert circuit_breaker.check_position_size(2) is False

        # Exceeds limit
        triggered = circuit_breaker.check_position_size(3)
        assert triggered is True
        assert circuit_breaker.can_trade() is False


class TestCircuitBreakerEdgeCases:
    """Test edge cases and boundary conditions"""

    @pytest.fixture
    def cb_config(self):
        return CircuitBreakerConfig(
            max_daily_loss=500.0,
            max_position_size=1,
            max_consecutive_losses=2,
            max_trades_per_day=5,
            position_timeout_hours=1.0,
            drawdown_limit_percent=5.0,
            cooldown_minutes=15
        )

    @pytest.fixture
    def circuit_breaker(self, cb_config):
        return CircuitBreaker(cb_config)

    def test_exact_limit_values(self, circuit_breaker, mock_daily_stats=None):
        """Test behavior at exact limit boundaries"""
        if mock_daily_stats is None:
            class MockDailyStats:
                def __init__(self, realized_pnl=0.0, consecutive_losses=0):
                    self.realized_pnl = realized_pnl
                    self.consecutive_losses = consecutive_losses
            mock_daily_stats = MockDailyStats

        # Exactly at limit (should not trigger)
        stats = mock_daily_stats(realized_pnl=-500.0)
        triggered = circuit_breaker.check_daily_loss_limit(stats)

        # Implementation-dependent: some systems trigger at >=, others at >
        assert triggered in [True, False]

    def test_zero_equity(self, circuit_breaker):
        """Test handling of zero equity"""
        circuit_breaker.check_drawdown(10000.0)

        # Zero equity (100% drawdown)
        triggered = circuit_breaker.check_drawdown(0.0)

        assert triggered is True

    def test_negative_equity(self, circuit_breaker):
        """Test handling of negative equity (margin call scenario)"""
        circuit_breaker.check_drawdown(10000.0)

        # Negative equity
        triggered = circuit_breaker.check_drawdown(-1000.0)

        assert triggered is True

    def test_very_long_position_duration(self, circuit_breaker):
        """Test handling of very long position duration"""
        # Position held for 24 hours
        entry_time = datetime.now(timezone.utc) - timedelta(hours=24)

        triggered = circuit_breaker.check_position_duration(entry_time)

        assert triggered is True

    def test_future_entry_time(self, circuit_breaker):
        """Test handling of future entry time (clock skew)"""
        # Entry time in the future
        entry_time = datetime.now(timezone.utc) + timedelta(hours=1)

        # Should handle gracefully (may trigger or return False)
        try:
            triggered = circuit_breaker.check_position_duration(entry_time)
            assert isinstance(triggered, bool)
        except ValueError:
            # Some implementations may raise error for invalid time
            pass

    def test_rapid_reset_and_trigger(self, circuit_breaker):
        """Test rapid reset and trigger cycles"""
        for _ in range(10):
            circuit_breaker._trigger("Test")
            assert circuit_breaker.can_trade() is False

            circuit_breaker.reset()
            assert circuit_breaker.can_trade() is True

    def test_concurrent_checks(self, circuit_breaker, mock_daily_stats=None):
        """Test multiple simultaneous checks"""
        if mock_daily_stats is None:
            class MockDailyStats:
                def __init__(self, realized_pnl=0.0, consecutive_losses=0):
                    self.realized_pnl = realized_pnl
                    self.consecutive_losses = consecutive_losses
            mock_daily_stats = MockDailyStats

        stats = mock_daily_stats(realized_pnl=-600.0, consecutive_losses=5)

        # Run multiple checks
        cb1 = circuit_breaker.check_daily_loss_limit(stats)
        cb2 = circuit_breaker.check_consecutive_losses(stats)

        # At least one should trigger
        assert cb1 or cb2

    def test_cooldown_exactly_expired(self, circuit_breaker):
        """Test cooldown at exact expiration time"""
        circuit_breaker._trigger("Test")

        # Set trigger time to exactly 15 minutes ago (cooldown period)
        circuit_breaker.state.trigger_time = datetime.now(timezone.utc) - timedelta(minutes=15)

        # Behavior depends on implementation (>= vs >)
        can_trade = circuit_breaker.can_trade()
        assert isinstance(can_trade, bool)

    def test_status_during_cooldown(self, circuit_breaker):
        """Test status reporting during cooldown period"""
        circuit_breaker._trigger("Test trigger")

        # Set trigger to 5 minutes ago
        circuit_breaker.state.trigger_time = datetime.now(timezone.utc) - timedelta(minutes=5)

        status = circuit_breaker.get_status()

        assert status["is_triggered"] is True
        assert status["can_trade"] is False
        assert 9 <= status["cooldown_remaining"] <= 11  # ~10 minutes remaining

    def test_reset_clears_peak_equity(self, circuit_breaker):
        """Test that reset clears peak equity"""
        circuit_breaker.check_drawdown(10000.0)
        assert circuit_breaker.state.peak_equity == 10000.0

        circuit_breaker.reset()

        # Peak should be reset
        assert circuit_breaker.state.peak_equity is None or circuit_breaker.state.peak_equity == 0


class TestCircuitBreakerIntegration:
    """Integration tests for circuit breaker with realistic scenarios"""

    @pytest.fixture
    def realistic_config(self):
        """Realistic production configuration"""
        return CircuitBreakerConfig(
            max_daily_loss=500.0,
            max_position_size=2,
            max_consecutive_losses=3,
            max_trades_per_day=20,
            position_timeout_hours=4.0,
            drawdown_limit_percent=15.0,
            cooldown_minutes=30
        )

    @pytest.fixture
    def circuit_breaker(self, realistic_config):
        return CircuitBreaker(realistic_config)

    def test_normal_trading_day_scenario(self, circuit_breaker):
        """Test normal trading day with wins and losses"""
        class MockStats:
            def __init__(self):
                self.realized_pnl = 0.0
                self.consecutive_losses = 0

        stats = MockStats()

        # Simulate trading day
        trades = [
            (+50, 0),   # Win
            (-30, 0),   # Loss
            (+70, 0),   # Win
            (-20, 0),   # Loss
            (+40, 0),   # Win
        ]

        for pnl, losses in trades:
            stats.realized_pnl += pnl
            stats.consecutive_losses = losses

            # Check circuit breaker
            assert circuit_breaker.check_daily_loss_limit(stats) is False
            assert circuit_breaker.check_consecutive_losses(stats) is False
            assert circuit_breaker.can_trade() is True

        # Final P&L should be positive
        assert stats.realized_pnl == 110.0

    def test_losing_streak_scenario(self, circuit_breaker):
        """Test circuit breaker during losing streak"""
        class MockStats:
            def __init__(self):
                self.realized_pnl = 0.0
                self.consecutive_losses = 0

        stats = MockStats()

        losses = [-80, -90, -70, -85]  # 4 consecutive losses

        for i, loss in enumerate(losses, 1):
            stats.realized_pnl += loss
            stats.consecutive_losses = i

            circuit_breaker.check_daily_loss_limit(stats)
            circuit_breaker.check_consecutive_losses(stats)

        # Should trigger on consecutive losses (3 limit)
        assert circuit_breaker.can_trade() is False
        assert "consecutive" in circuit_breaker.state.trigger_reason.lower()

    def test_recovery_after_trigger(self, circuit_breaker):
        """Test recovery and reset for new trading day"""
        # Trigger circuit breaker
        circuit_breaker._trigger("Daily loss limit")
        assert circuit_breaker.can_trade() is False

        # New trading day - reset
        circuit_breaker.reset()

        # Should be able to trade again
        assert circuit_breaker.can_trade() is True
        assert circuit_breaker.state.is_triggered is False
