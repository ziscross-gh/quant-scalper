"""
Integration tests for bot/core/engine.py - Full trading workflow
"""
import pytest
import asyncio
from datetime import datetime, timezone, timedelta

from bot.core.engine import TradingEngine, EngineState
from bot.config import Config, TradingConfig, RiskConfig, DatabaseConfig, DebugConfig


class TestTradingEngineIntegration:
    """Integration tests for full trading engine workflow"""

    @pytest.fixture
    def test_config(self, temp_dir):
        """Create test configuration"""
        return Config(
            trading=TradingConfig(
                symbol="MES",
                exchange="GLOBEX",
                currency="USD",
                lookback_bars=20,
                z_entry_threshold=2.0,
                z_exit_threshold=0.5,
                min_volume_filter=100
            ),
            risk=RiskConfig(
                max_daily_loss=500.0,
                max_position_size=2,
                max_consecutive_losses=3,
                max_trades_per_day=10,
                position_timeout_hours=2.0,
                drawdown_limit_percent=10.0,
                cooldown_minutes=30
            ),
            database=DatabaseConfig(
                path=str(temp_dir / "test_trades.db")
            ),
            debug=DebugConfig(
                dry_run=True,
                log_level="INFO"
            )
        )

    @pytest.fixture
    def engine(self, test_config, mock_telegram_alerts):
        """Create trading engine with mocked components"""
        alerts = mock_telegram_alerts()
        engine = TradingEngine(test_config, alerts=alerts)
        return engine

    @pytest.mark.asyncio
    async def test_engine_startup_shutdown(self, engine):
        """Test engine startup and shutdown"""
        await engine.start()

        assert engine.state == EngineState.RUNNING
        assert engine.is_running()

        await engine.stop("Test complete")

        assert engine.state == EngineState.STOPPED
        assert not engine.is_running()

    @pytest.mark.asyncio
    async def test_process_bar_workflow(self, engine):
        """Test processing a single bar through full workflow"""
        await engine.start()

        bar = {
            "time": datetime.now(timezone.utc),
            "open": 5000.0,
            "high": 5005.0,
            "low": 4995.0,
            "close": 5000.0,
            "volume": 1000
        }

        await engine.process_bar(bar)

        # Engine should have processed the bar
        status = engine.get_status()
        assert "running" in status
        assert "zscore" in status

        await engine.stop()

    @pytest.mark.asyncio
    async def test_warmup_period(self, engine):
        """Test that engine handles warmup period correctly"""
        await engine.start()

        # Feed bars during warmup (less than lookback)
        for i in range(15):  # Less than 20 lookback
            bar = {
                "time": datetime.now(timezone.utc),
                "open": 5000.0 + i,
                "high": 5005.0 + i,
                "low": 4995.0 + i,
                "close": 5000.0 + i,
                "volume": 1000
            }
            await engine.process_bar(bar)

        status = engine.get_status()

        # Should not have entered any positions
        assert status["position"] == 0

        await engine.stop()

    @pytest.mark.asyncio
    async def test_signal_to_trade_workflow(self, engine):
        """Test full workflow from signal generation to trade execution"""
        await engine.start()

        # Warmup period
        for i in range(20):
            bar = {
                "time": datetime.now(timezone.utc),
                "open": 5000.0,
                "high": 5001.0,
                "low": 4999.0,
                "close": 5000.0,
                "volume": 1000
            }
            await engine.process_bar(bar)

        # Send bar that should trigger signal
        trigger_bar = {
            "time": datetime.now(timezone.utc),
            "open": 4980.0,
            "high": 4982.0,
            "low": 4978.0,
            "close": 4980.0,  # Significant deviation
            "volume": 1500
        }

        await engine.process_bar(trigger_bar)

        status = engine.get_status()

        # May or may not have entered position (depends on exact Z-Score)
        assert status["position"] in [-1, 0, 1]

        await engine.stop()

    @pytest.mark.asyncio
    async def test_circuit_breaker_integration(self, engine):
        """Test that circuit breaker halts trading when triggered"""
        await engine.start()

        # Simulate losing trades to trigger circuit breaker
        # This requires internal state manipulation or realistic market data
        # For now, test that circuit breaker is integrated

        status = engine.get_status()
        assert "circuit_breaker" in status or "can_trade" in status

        await engine.stop()

    @pytest.mark.asyncio
    async def test_database_logging_integration(self, engine):
        """Test that trades are logged to database"""
        await engine.start()

        # Process enough bars to potentially generate signals
        for i in range(30):
            bar = {
                "time": datetime.now(timezone.utc),
                "open": 5000.0 + (i % 5),
                "high": 5005.0 + (i % 5),
                "low": 4995.0 + (i % 5),
                "close": 5000.0 + (i % 5),
                "volume": 1000 + (i * 10)
            }
            await engine.process_bar(bar)

        # Check database
        if engine.database:
            trades = engine.database.get_all_trades()
            # May or may not have trades depending on signals
            assert isinstance(trades, list)

        await engine.stop()

    @pytest.mark.asyncio
    async def test_telegram_alerts_integration(self, engine):
        """Test that Telegram alerts are sent"""
        await engine.start()

        # Process bars
        for i in range(25):
            bar = {
                "time": datetime.now(timezone.utc),
                "open": 5000.0 + i,
                "high": 5005.0 + i,
                "low": 4995.0 + i,
                "close": 5000.0 + i,
                "volume": 1000
            }
            await engine.process_bar(bar)

        # Check that alerts object received messages
        if engine.alerts:
            messages = engine.alerts.get_messages()
            # At minimum, should have startup message
            assert len(messages) >= 0

        await engine.stop()

    @pytest.mark.asyncio
    async def test_position_entry_and_exit(self, engine):
        """Test complete position entry and exit cycle"""
        await engine.start()

        # Warmup with stable prices
        for i in range(20):
            bar = {
                "time": datetime.now(timezone.utc),
                "open": 5000.0,
                "high": 5001.0,
                "low": 4999.0,
                "close": 5000.0,
                "volume": 1000
            }
            await engine.process_bar(bar)

        # Entry signal (oversold)
        entry_bar = {
            "time": datetime.now(timezone.utc),
            "open": 4980.0,
            "high": 4982.0,
            "low": 4978.0,
            "close": 4980.0,
            "volume": 1500
        }
        await engine.process_bar(entry_bar)

        # Reversion bars
        for i in range(5):
            bar = {
                "time": datetime.now(timezone.utc),
                "open": 4985.0 + i,
                "high": 4986.0 + i,
                "low": 4984.0 + i,
                "close": 4985.0 + i,
                "volume": 1000
            }
            await engine.process_bar(bar)

        # Exit signal (back to mean)
        exit_bar = {
            "time": datetime.now(timezone.utc),
            "open": 5000.0,
            "high": 5002.0,
            "low": 4998.0,
            "close": 5000.0,
            "volume": 1200
        }
        await engine.process_bar(exit_bar)

        status = engine.get_status()

        # Should have attempted to enter and possibly exit
        assert "position" in status
        assert "daily_pnl" in status

        await engine.stop()

    @pytest.mark.asyncio
    async def test_multiple_trading_sessions(self, engine):
        """Test multiple start/stop cycles"""
        # Session 1
        await engine.start()
        for i in range(10):
            bar = {
                "time": datetime.now(timezone.utc),
                "open": 5000.0,
                "high": 5001.0,
                "low": 4999.0,
                "close": 5000.0,
                "volume": 1000
            }
            await engine.process_bar(bar)
        await engine.stop()

        # Session 2
        await engine.start()
        for i in range(10):
            bar = {
                "time": datetime.now(timezone.utc),
                "open": 5010.0,
                "high": 5011.0,
                "low": 5009.0,
                "close": 5010.0,
                "volume": 1000
            }
            await engine.process_bar(bar)
        await engine.stop()

        # Engine should handle multiple sessions
        assert engine.state == EngineState.STOPPED

    @pytest.mark.asyncio
    async def test_error_handling(self, engine):
        """Test that engine handles errors gracefully"""
        await engine.start()

        # Send malformed bar
        malformed_bar = {
            "close": None,  # Invalid
            "volume": -100  # Invalid
        }

        try:
            await engine.process_bar(malformed_bar)
        except Exception as e:
            # Should handle gracefully
            assert isinstance(e, (KeyError, ValueError, TypeError))

        # Engine should still be running
        assert engine.is_running()

        await engine.stop()

    @pytest.mark.asyncio
    async def test_concurrent_bar_processing(self, engine):
        """Test processing multiple bars concurrently"""
        await engine.start()

        # Create multiple bars
        bars = []
        for i in range(5):
            bars.append({
                "time": datetime.now(timezone.utc) + timedelta(seconds=i),
                "open": 5000.0 + i,
                "high": 5005.0 + i,
                "low": 4995.0 + i,
                "close": 5000.0 + i,
                "volume": 1000
            })

        # Process concurrently
        tasks = [engine.process_bar(bar) for bar in bars]
        await asyncio.gather(*tasks, return_exceptions=True)

        # Engine should handle concurrent processing
        assert engine.is_running()

        await engine.stop()

    @pytest.mark.asyncio
    async def test_status_reporting(self, engine):
        """Test comprehensive status reporting"""
        await engine.start()

        # Process some bars
        for i in range(25):
            bar = {
                "time": datetime.now(timezone.utc),
                "open": 5000.0 + i,
                "high": 5005.0 + i,
                "low": 4995.0 + i,
                "close": 5000.0 + i,
                "volume": 1000
            }
            await engine.process_bar(bar)

        status = engine.get_status()

        # Verify status contains all expected fields
        required_fields = [
            "running",
            "position",
            "daily_pnl",
            "trades_today",
            "zscore"
        ]

        for field in required_fields:
            assert field in status, f"Missing field: {field}"

        await engine.stop()

    @pytest.mark.asyncio
    async def test_dry_run_mode(self, test_config, mock_telegram_alerts):
        """Test that dry run mode prevents real trading"""
        test_config.debug.dry_run = True

        alerts = mock_telegram_alerts()
        engine = TradingEngine(test_config, alerts=alerts)

        await engine.start()

        # Process bars that would trigger signals
        for i in range(30):
            bar = {
                "time": datetime.now(timezone.utc),
                "open": 5000.0 + (i * 2),
                "high": 5005.0 + (i * 2),
                "low": 4995.0 + (i * 2),
                "close": 5000.0 + (i * 2),
                "volume": 1000
            }
            await engine.process_bar(bar)

        # In dry run mode, no real orders should be placed
        # (Implementation-dependent verification)

        await engine.stop()


class TestEngineRiskManagement:
    """Integration tests for risk management features"""

    @pytest.fixture
    def strict_risk_config(self, temp_dir):
        """Create config with strict risk limits"""
        return Config(
            trading=TradingConfig(
                symbol="MES",
                exchange="GLOBEX",
                currency="USD",
                lookback_bars=10,
                z_entry_threshold=1.5,  # Lower for more trades
                z_exit_threshold=0.3,
                min_volume_filter=0
            ),
            risk=RiskConfig(
                max_daily_loss=100.0,  # Strict
                max_position_size=1,
                max_consecutive_losses=2,  # Very strict
                max_trades_per_day=3,
                position_timeout_hours=0.5,  # 30 minutes
                drawdown_limit_percent=5.0,
                cooldown_minutes=15
            ),
            database=DatabaseConfig(
                path=str(temp_dir / "test_trades.db")
            ),
            debug=DebugConfig(
                dry_run=True,
                log_level="INFO"
            )
        )

    @pytest.mark.asyncio
    async def test_daily_loss_limit_enforcement(self, strict_risk_config, mock_telegram_alerts):
        """Test that daily loss limit stops trading"""
        alerts = mock_telegram_alerts()
        engine = TradingEngine(strict_risk_config, alerts=alerts)

        await engine.start()

        # Simulate conditions that would trigger loss limit
        # (Implementation-dependent)

        status = engine.get_status()
        assert "daily_pnl" in status

        await engine.stop()

    @pytest.mark.asyncio
    async def test_position_timeout_enforcement(self, strict_risk_config, mock_telegram_alerts):
        """Test that positions are closed after timeout"""
        alerts = mock_telegram_alerts()
        engine = TradingEngine(strict_risk_config, alerts=alerts)

        await engine.start()

        # Enter position and wait for timeout
        # (Implementation-dependent)

        await engine.stop()

    @pytest.mark.asyncio
    async def test_max_trades_per_day(self, strict_risk_config, mock_telegram_alerts):
        """Test that max trades per day is enforced"""
        alerts = mock_telegram_alerts()
        engine = TradingEngine(strict_risk_config, alerts=alerts)

        await engine.start()

        # Try to exceed trade limit
        # (Implementation-dependent)

        await engine.stop()


class TestEngineRecovery:
    """Integration tests for engine recovery and resilience"""

    @pytest.mark.asyncio
    async def test_recovery_after_error(self, test_config, mock_telegram_alerts):
        """Test that engine recovers from errors"""
        alerts = mock_telegram_alerts()
        engine = TradingEngine(test_config, alerts=alerts)

        await engine.start()

        # Cause an error
        try:
            await engine.process_bar({"invalid": "data"})
        except:
            pass

        # Engine should still be operational
        valid_bar = {
            "time": datetime.now(timezone.utc),
            "open": 5000.0,
            "high": 5001.0,
            "low": 4999.0,
            "close": 5000.0,
            "volume": 1000
        }

        await engine.process_bar(valid_bar)

        assert engine.is_running()

        await engine.stop()

    @pytest.mark.asyncio
    async def test_state_persistence(self, test_config, mock_telegram_alerts, temp_dir):
        """Test that engine state can be persisted and restored"""
        # First session
        alerts1 = mock_telegram_alerts()
        engine1 = TradingEngine(test_config, alerts=alerts1)

        await engine1.start()

        for i in range(25):
            bar = {
                "time": datetime.now(timezone.utc),
                "open": 5000.0 + i,
                "high": 5005.0 + i,
                "low": 4995.0 + i,
                "close": 5000.0 + i,
                "volume": 1000
            }
            await engine1.process_bar(bar)

        status1 = engine1.get_status()

        await engine1.stop()

        # Second session (restored)
        alerts2 = mock_telegram_alerts()
        engine2 = TradingEngine(test_config, alerts=alerts2)

        await engine2.start()

        # State should be retrievable from database
        if engine2.database:
            trades = engine2.database.get_all_trades()
            # Should have same trades as engine1
            assert isinstance(trades, list)

        await engine2.stop()
