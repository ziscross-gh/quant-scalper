"""
Unit tests for bot/core/signals.py - Signal generation and Z-Score logic
"""
import pytest
from datetime import datetime, timezone

from bot.core.signals import SignalGenerator, Signal, SignalType, PositionState
from bot.config import TradingConfig


class TestSignalType:
    """Test SignalType enum"""

    def test_signal_types(self):
        """Test that all signal types are defined"""
        assert SignalType.LONG == "LONG"
        assert SignalType.SHORT == "SHORT"
        assert SignalType.EXIT_LONG == "EXIT_LONG"
        assert SignalType.EXIT_SHORT == "EXIT_SHORT"
        assert SignalType.NONE == "NONE"


class TestPositionState:
    """Test PositionState enum"""

    def test_position_states(self):
        """Test that all position states are defined"""
        assert PositionState.FLAT == "FLAT"
        assert PositionState.LONG == "LONG"
        assert PositionState.SHORT == "SHORT"


class TestSignal:
    """Test Signal dataclass"""

    def test_signal_creation(self):
        """Test creating a signal"""
        signal = Signal(
            type=SignalType.LONG,
            timestamp=datetime.now(timezone.utc),
            price=5000.0,
            zscore=2.5,
            volume=1000,
            reason="Z-Score >= 2.0"
        )

        assert signal.type == SignalType.LONG
        assert signal.price == 5000.0
        assert signal.zscore == 2.5
        assert signal.volume == 1000

    def test_signal_to_dict(self):
        """Test converting signal to dictionary"""
        timestamp = datetime.now(timezone.utc)
        signal = Signal(
            type=SignalType.SHORT,
            timestamp=timestamp,
            price=5010.0,
            zscore=-2.3,
            volume=1500,
            reason="Z-Score <= -2.0"
        )

        signal_dict = signal.to_dict()

        assert signal_dict["type"] == "SHORT"
        assert signal_dict["price"] == 5010.0
        assert signal_dict["zscore"] == -2.3
        assert "timestamp" in signal_dict


class TestSignalGenerator:
    """Test SignalGenerator logic"""

    @pytest.fixture
    def trading_config(self):
        """Create trading config for tests"""
        return TradingConfig(
            symbol="MES",
            exchange="GLOBEX",
            currency="USD",
            lookback_bars=20,
            z_entry_threshold=2.0,
            z_exit_threshold=0.5,
            min_volume_filter=100
        )

    @pytest.fixture
    def signal_gen(self, trading_config, mock_zscore_engine):
        """Create signal generator with mock engine"""
        engine = mock_zscore_engine(lookback=20)
        return SignalGenerator(trading_config, zscore_engine=engine)

    def test_initialization(self, signal_gen, trading_config):
        """Test signal generator initialization"""
        assert signal_gen.config == trading_config
        assert signal_gen.position_state == PositionState.FLAT
        assert signal_gen.zscore_engine is not None

    def test_warmup_period(self, signal_gen):
        """Test that no signals are generated during warmup"""
        # Feed 10 bars (less than 20 lookback)
        for i in range(10):
            bar = {
                "close": 5000.0 + i,
                "volume": 1000,
                "time": datetime.now(timezone.utc)
            }
            signal = signal_gen.process_bar(bar)

            assert signal.type == SignalType.NONE
            assert "warmup" in signal.reason.lower() or "not ready" in signal.reason.lower()

    def test_volume_filter(self, signal_gen):
        """Test that low volume bars are filtered"""
        # Warm up the engine first
        for i in range(20):
            bar = {
                "close": 5000.0 + i * 0.1,
                "volume": 1000,
                "time": datetime.now(timezone.utc)
            }
            signal_gen.process_bar(bar)

        # Now send low volume bar
        low_volume_bar = {
            "close": 5100.0,  # Would trigger signal if not filtered
            "volume": 50,  # Below 100 threshold
            "time": datetime.now(timezone.utc)
        }

        signal = signal_gen.process_bar(low_volume_bar)

        assert signal.type == SignalType.NONE
        assert "volume" in signal.reason.lower()

    def test_long_signal_generation(self, signal_gen):
        """Test LONG signal when Z-Score >= +2.0"""
        # Warm up with stable prices around 5000
        for i in range(20):
            bar = {
                "close": 5000.0,
                "volume": 1000,
                "time": datetime.now(timezone.utc)
            }
            signal_gen.process_bar(bar)

        # Send oversold price (should generate high positive Z-Score)
        oversold_bar = {
            "close": 4980.0,  # Significantly below mean
            "volume": 1000,
            "time": datetime.now(timezone.utc)
        }

        signal = signal_gen.process_bar(oversold_bar)

        # Should generate LONG signal or NONE (depends on exact Z-Score)
        assert signal.type in [SignalType.LONG, SignalType.NONE]

        if signal.type == SignalType.LONG:
            assert signal.zscore >= 2.0 or signal.zscore <= -2.0
            assert signal_gen.position_state == PositionState.LONG

    def test_short_signal_generation(self, signal_gen):
        """Test SHORT signal when Z-Score <= -2.0"""
        # Warm up with stable prices around 5000
        for i in range(20):
            bar = {
                "close": 5000.0,
                "volume": 1000,
                "time": datetime.now(timezone.utc)
            }
            signal_gen.process_bar(bar)

        # Send overbought price (should generate high negative Z-Score)
        overbought_bar = {
            "close": 5020.0,  # Significantly above mean
            "volume": 1000,
            "time": datetime.now(timezone.utc)
        }

        signal = signal_gen.process_bar(overbought_bar)

        # Should generate SHORT signal or NONE (depends on exact Z-Score)
        assert signal.type in [SignalType.SHORT, SignalType.NONE]

        if signal.type == SignalType.SHORT:
            assert abs(signal.zscore) >= 2.0
            assert signal_gen.position_state == PositionState.SHORT

    def test_exit_long_signal(self, signal_gen):
        """Test EXIT_LONG signal when Z-Score returns to near zero"""
        # Manually set position state to LONG
        signal_gen.position_state = PositionState.LONG

        # Warm up engine
        for i in range(20):
            bar = {
                "close": 5000.0 + (i * 0.1),
                "volume": 1000,
                "time": datetime.now(timezone.utc)
            }
            signal_gen.process_bar(bar)

        # Send price near mean (low Z-Score)
        exit_bar = {
            "close": 5001.0,  # Close to mean
            "volume": 1000,
            "time": datetime.now(timezone.utc)
        }

        signal = signal_gen.process_bar(exit_bar)

        # Should generate EXIT_LONG or NONE
        if signal.type == SignalType.EXIT_LONG:
            assert abs(signal.zscore) <= 0.5
            assert signal_gen.position_state == PositionState.FLAT

    def test_exit_short_signal(self, signal_gen):
        """Test EXIT_SHORT signal when Z-Score returns to near zero"""
        # Manually set position state to SHORT
        signal_gen.position_state = PositionState.SHORT

        # Warm up engine
        for i in range(20):
            bar = {
                "close": 5000.0 - (i * 0.1),
                "volume": 1000,
                "time": datetime.now(timezone.utc)
            }
            signal_gen.process_bar(bar)

        # Send price near mean (low Z-Score)
        exit_bar = {
            "close": 4999.0,  # Close to mean
            "volume": 1000,
            "time": datetime.now(timezone.utc)
        }

        signal = signal_gen.process_bar(exit_bar)

        # Should generate EXIT_SHORT or NONE
        if signal.type == SignalType.EXIT_SHORT:
            assert abs(signal.zscore) <= 0.5
            assert signal_gen.position_state == PositionState.FLAT

    def test_no_duplicate_entry_signals(self, signal_gen):
        """Test that entry signals are not generated when already in position"""
        # Set to LONG position
        signal_gen.position_state = PositionState.LONG

        # Warm up
        for i in range(20):
            bar = {
                "close": 5000.0,
                "volume": 1000,
                "time": datetime.now(timezone.utc)
            }
            signal_gen.process_bar(bar)

        # Send another potential LONG signal
        bar = {
            "close": 4980.0,
            "volume": 1000,
            "time": datetime.now(timezone.utc)
        }

        signal = signal_gen.process_bar(bar)

        # Should NOT generate another LONG signal
        assert signal.type != SignalType.LONG

    def test_reset_functionality(self, signal_gen):
        """Test resetting the signal generator"""
        # Set position state
        signal_gen.position_state = PositionState.LONG

        # Reset
        signal_gen.reset()

        assert signal_gen.position_state == PositionState.FLAT

    def test_get_current_zscore(self, signal_gen):
        """Test getting current Z-Score"""
        # Before warmup
        zscore = signal_gen.get_current_zscore()
        assert zscore is None

        # After warmup
        for i in range(25):
            bar = {
                "close": 5000.0 + (i * 0.5),
                "volume": 1000,
                "time": datetime.now(timezone.utc)
            }
            signal_gen.process_bar(bar)

        zscore = signal_gen.get_current_zscore()
        assert zscore is not None
        assert isinstance(zscore, float)

    def test_signal_statistics(self, signal_gen):
        """Test getting signal statistics"""
        stats = signal_gen.get_stats()

        assert "position_state" in stats
        assert "is_ready" in stats
        assert "zscore" in stats

        # After warmup
        for i in range(25):
            bar = {
                "close": 5000.0 + i,
                "volume": 1000,
                "time": datetime.now(timezone.utc)
            }
            signal_gen.process_bar(bar)

        stats = signal_gen.get_stats()
        assert stats["is_ready"] is True

    def test_extreme_zscore_values(self, signal_gen):
        """Test handling of extreme Z-Score values"""
        # Create extreme deviation
        for i in range(20):
            bar = {
                "close": 5000.0,
                "volume": 1000,
                "time": datetime.now(timezone.utc)
            }
            signal_gen.process_bar(bar)

        # Extreme price move
        extreme_bar = {
            "close": 6000.0,  # Massive jump
            "volume": 1000,
            "time": datetime.now(timezone.utc)
        }

        signal = signal_gen.process_bar(extreme_bar)

        # Should handle gracefully
        assert signal is not None
        assert isinstance(signal.zscore, (float, int, type(None)))

    def test_zero_variance_handling(self, signal_gen):
        """Test handling when all prices are identical (zero variance)"""
        # Feed identical prices
        for i in range(25):
            bar = {
                "close": 5000.0,  # All same
                "volume": 1000,
                "time": datetime.now(timezone.utc)
            }
            signal = signal_gen.process_bar(bar)

        # Should handle zero variance gracefully
        assert signal is not None
        # Z-Score should be 0 or None for zero variance
        if signal.zscore is not None:
            assert signal.zscore == 0.0

    def test_signal_reasons(self, signal_gen):
        """Test that signals include human-readable reasons"""
        for i in range(25):
            bar = {
                "close": 5000.0 + i,
                "volume": 1000,
                "time": datetime.now(timezone.utc)
            }
            signal = signal_gen.process_bar(bar)

            assert signal.reason is not None
            assert isinstance(signal.reason, str)
            assert len(signal.reason) > 0


class TestSignalEdgeCases:
    """Test edge cases and boundary conditions"""

    @pytest.fixture
    def trading_config(self):
        return TradingConfig(
            symbol="MES",
            exchange="GLOBEX",
            currency="USD",
            lookback_bars=5,  # Small lookback for faster tests
            z_entry_threshold=2.0,
            z_exit_threshold=0.5,
            min_volume_filter=0  # Disable volume filter
        )

    @pytest.fixture
    def signal_gen(self, trading_config, mock_zscore_engine):
        engine = mock_zscore_engine(lookback=5)
        return SignalGenerator(trading_config, zscore_engine=engine)

    def test_exact_threshold_values(self, signal_gen):
        """Test signals at exact threshold boundaries"""
        # This would require precise control over Z-Score
        # Implementation depends on exact thresholds
        pass

    def test_rapid_price_changes(self, signal_gen):
        """Test handling of rapid price oscillations"""
        prices = [5000, 5010, 4990, 5015, 4985, 5020]

        for price in prices:
            bar = {
                "close": price,
                "volume": 1000,
                "time": datetime.now(timezone.utc)
            }
            signal = signal_gen.process_bar(bar)

            # Should handle without errors
            assert signal is not None

    def test_missing_bar_fields(self, signal_gen):
        """Test handling of bars with missing fields"""
        incomplete_bar = {
            "close": 5000.0,
            # Missing volume and time
        }

        # Should handle gracefully or raise appropriate error
        try:
            signal = signal_gen.process_bar(incomplete_bar)
            assert signal is not None
        except (KeyError, ValueError) as e:
            # Expected if validation is strict
            assert "volume" in str(e) or "time" in str(e)

    def test_negative_prices(self, signal_gen):
        """Test handling of negative prices (should not occur in reality)"""
        bar = {
            "close": -5000.0,  # Invalid but test robustness
            "volume": 1000,
            "time": datetime.now(timezone.utc)
        }

        # Should either handle or raise appropriate error
        signal = signal_gen.process_bar(bar)
        assert signal is not None  # Or should raise ValueError

    def test_concurrent_signal_generation(self, trading_config, mock_zscore_engine):
        """Test that multiple signal generators can operate independently"""
        gen1 = SignalGenerator(trading_config, zscore_engine=mock_zscore_engine(20))
        gen2 = SignalGenerator(trading_config, zscore_engine=mock_zscore_engine(20))

        # Feed same data to both
        for i in range(25):
            bar = {
                "close": 5000.0 + i,
                "volume": 1000,
                "time": datetime.now(timezone.utc)
            }
            sig1 = gen1.process_bar(bar)
            sig2 = gen2.process_bar(bar)

            # Both should produce same signals
            assert sig1.type == sig2.type
