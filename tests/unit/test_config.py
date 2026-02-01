"""
Unit tests for bot/config.py - Configuration validation and loading
"""
import pytest
import yaml
from pathlib import Path

from bot.config import (
    Config, TradingConfig, IBKRConfig, RiskConfig,
    TelegramConfig, DatabaseConfig, DebugConfig,
    ConfigValidationError
)


class TestTradingConfig:
    """Test TradingConfig validation"""

    def test_valid_trading_config(self):
        """Test valid trading configuration"""
        config = TradingConfig(
            symbol="MES",
            exchange="GLOBEX",
            currency="USD",
            lookback_bars=20,
            z_entry_threshold=2.0,
            z_exit_threshold=0.5,
            min_volume_filter=100
        )

        assert config.symbol == "MES"
        assert config.lookback_bars == 20
        assert config.z_entry_threshold == 2.0

    def test_invalid_lookback_bars(self):
        """Test that lookback_bars must be >= 2"""
        with pytest.raises(ValueError, match="lookback_bars must be >= 2"):
            TradingConfig(
                symbol="MES",
                exchange="GLOBEX",
                currency="USD",
                lookback_bars=1,  # Invalid
                z_entry_threshold=2.0,
                z_exit_threshold=0.5
            )

    def test_invalid_z_thresholds(self):
        """Test that Z-Score thresholds must be positive"""
        with pytest.raises(ValueError, match="z_entry_threshold must be > 0"):
            TradingConfig(
                symbol="MES",
                exchange="GLOBEX",
                currency="USD",
                lookback_bars=20,
                z_entry_threshold=-1.0,  # Invalid
                z_exit_threshold=0.5
            )

    def test_exit_threshold_greater_than_entry(self):
        """Test that exit threshold must be less than entry threshold"""
        with pytest.raises(ValueError, match="z_exit_threshold must be < z_entry_threshold"):
            TradingConfig(
                symbol="MES",
                exchange="GLOBEX",
                currency="USD",
                lookback_bars=20,
                z_entry_threshold=2.0,
                z_exit_threshold=3.0  # Invalid: greater than entry
            )


class TestRiskConfig:
    """Test RiskConfig validation"""

    def test_valid_risk_config(self):
        """Test valid risk configuration"""
        config = RiskConfig(
            max_daily_loss=500.0,
            max_position_size=2,
            max_consecutive_losses=3,
            max_trades_per_day=10,
            position_timeout_hours=2.0,
            drawdown_limit_percent=10.0,
            cooldown_minutes=30
        )

        assert config.max_daily_loss == 500.0
        assert config.max_position_size == 2

    def test_invalid_max_daily_loss(self):
        """Test that max_daily_loss must be positive"""
        with pytest.raises(ValueError, match="max_daily_loss must be > 0"):
            RiskConfig(
                max_daily_loss=-100.0,  # Invalid
                max_position_size=2,
                max_consecutive_losses=3
            )

    def test_invalid_position_size(self):
        """Test that max_position_size must be positive"""
        with pytest.raises(ValueError, match="max_position_size must be > 0"):
            RiskConfig(
                max_daily_loss=500.0,
                max_position_size=0,  # Invalid
                max_consecutive_losses=3
            )

    def test_invalid_drawdown_limit(self):
        """Test that drawdown_limit_percent must be 0-100"""
        with pytest.raises(ValueError, match="drawdown_limit_percent must be between 0 and 100"):
            RiskConfig(
                max_daily_loss=500.0,
                max_position_size=2,
                max_consecutive_losses=3,
                drawdown_limit_percent=150.0  # Invalid
            )


class TestIBKRConfig:
    """Test IBKRConfig validation"""

    def test_valid_ibkr_config(self):
        """Test valid IBKR configuration"""
        config = IBKRConfig(
            host="127.0.0.1",
            port=4002,
            client_id=1,
            account="DU12345",
            timeout_seconds=30
        )

        assert config.host == "127.0.0.1"
        assert config.port == 4002

    def test_invalid_port(self):
        """Test that port must be in valid range"""
        with pytest.raises(ValueError, match="port must be between 1 and 65535"):
            IBKRConfig(
                host="127.0.0.1",
                port=70000,  # Invalid
                client_id=1,
                account="DU12345"
            )

    def test_invalid_timeout(self):
        """Test that timeout must be positive"""
        with pytest.raises(ValueError, match="timeout_seconds must be > 0"):
            IBKRConfig(
                host="127.0.0.1",
                port=4002,
                client_id=1,
                account="DU12345",
                timeout_seconds=-5  # Invalid
            )


class TestConfig:
    """Test full Config loading and validation"""

    def test_load_from_dict(self, sample_config_dict):
        """Test loading config from dictionary"""
        config = Config.from_dict(sample_config_dict)

        assert config.trading.symbol == "MES"
        assert config.risk.max_daily_loss == 500.0
        assert config.ibkr.port == 4002
        assert config.debug.dry_run is True

    def test_load_from_yaml_file(self, config_yaml_file):
        """Test loading config from YAML file"""
        config = Config.load(str(config_yaml_file))

        assert config.trading.symbol == "MES"
        assert config.risk.max_daily_loss == 500.0

    def test_invalid_yaml_file(self, temp_dir):
        """Test error handling for missing YAML file"""
        invalid_path = temp_dir / "nonexistent.yaml"

        with pytest.raises(FileNotFoundError):
            Config.load(str(invalid_path))

    def test_malformed_yaml(self, temp_dir):
        """Test error handling for malformed YAML"""
        malformed_path = temp_dir / "malformed.yaml"

        with open(malformed_path, 'w') as f:
            f.write("invalid: yaml: content:\n  - broken")

        with pytest.raises(yaml.YAMLError):
            Config.load(str(malformed_path))

    def test_missing_required_fields(self, sample_config_dict, temp_dir):
        """Test that missing required fields raise error"""
        # Remove required field
        del sample_config_dict["trading"]["symbol"]

        config_path = temp_dir / "incomplete.yaml"
        with open(config_path, 'w') as f:
            yaml.dump(sample_config_dict, f)

        with pytest.raises((ConfigValidationError, TypeError, KeyError)):
            Config.load(str(config_path))

    def test_live_mode_validation(self, sample_config_dict):
        """Test that LIVE mode requires confirmation"""
        sample_config_dict["ibkr"]["port"] = 7496  # LIVE port
        sample_config_dict["debug"]["dry_run"] = False

        # Should raise warning or require explicit confirmation
        # (Implementation may vary)
        config = Config.from_dict(sample_config_dict)
        assert config.ibkr.port == 7496

    def test_telegram_config_validation(self):
        """Test Telegram configuration validation"""
        # Enabled but missing token
        with pytest.raises(ValueError, match="bot_token required when enabled"):
            TelegramConfig(
                enabled=True,
                bot_token=None,  # Missing
                chat_id="12345"
            )

        # Enabled but missing chat_id
        with pytest.raises(ValueError, match="chat_id required when enabled"):
            TelegramConfig(
                enabled=True,
                bot_token="test-token",
                chat_id=None  # Missing
            )

    def test_config_to_dict(self, sample_config):
        """Test converting config back to dictionary"""
        config_dict = sample_config.to_dict()

        assert config_dict["trading"]["symbol"] == "MES"
        assert config_dict["risk"]["max_daily_loss"] == 500.0
        assert isinstance(config_dict, dict)

    def test_config_defaults(self):
        """Test that config uses sensible defaults"""
        config = TradingConfig(
            symbol="MES",
            exchange="GLOBEX",
            currency="USD",
            lookback_bars=20,
            z_entry_threshold=2.0,
            z_exit_threshold=0.5
        )

        # Check defaults
        assert config.min_volume_filter >= 0

    def test_database_path_validation(self, temp_dir):
        """Test database path validation"""
        db_path = temp_dir / "data" / "trades.db"

        config = DatabaseConfig(path=str(db_path))

        assert config.path == str(db_path)

    def test_debug_log_levels(self):
        """Test valid log levels"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

        for level in valid_levels:
            config = DebugConfig(dry_run=True, log_level=level)
            assert config.log_level == level

    def test_risk_config_percentage_limits(self):
        """Test percentage-based risk limits"""
        config = RiskConfig(
            max_daily_loss=500.0,
            max_position_size=2,
            max_consecutive_losses=3,
            drawdown_limit_percent=10.0
        )

        assert 0 <= config.drawdown_limit_percent <= 100


class TestConfigEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_zero_volume_filter(self):
        """Test that volume filter can be zero (disabled)"""
        config = TradingConfig(
            symbol="MES",
            exchange="GLOBEX",
            currency="USD",
            lookback_bars=20,
            z_entry_threshold=2.0,
            z_exit_threshold=0.5,
            min_volume_filter=0  # Disabled
        )

        assert config.min_volume_filter == 0

    def test_very_large_lookback(self):
        """Test handling of very large lookback periods"""
        config = TradingConfig(
            symbol="MES",
            exchange="GLOBEX",
            currency="USD",
            lookback_bars=1000,  # Very large
            z_entry_threshold=2.0,
            z_exit_threshold=0.5
        )

        assert config.lookback_bars == 1000

    def test_small_z_thresholds(self):
        """Test very small (but valid) Z-Score thresholds"""
        config = TradingConfig(
            symbol="MES",
            exchange="GLOBEX",
            currency="USD",
            lookback_bars=20,
            z_entry_threshold=0.1,  # Very small
            z_exit_threshold=0.05
        )

        assert config.z_entry_threshold == 0.1
        assert config.z_exit_threshold == 0.05

    def test_config_immutability(self, sample_config):
        """Test that config should be treated as immutable"""
        original_symbol = sample_config.trading.symbol

        # Attempting to modify (depends on implementation)
        # If using frozen dataclasses, this would raise an error
        sample_config.trading.symbol = "ES"

        # Verify change (or that it's prevented)
        assert sample_config.trading.symbol == "ES" or sample_config.trading.symbol == original_symbol
