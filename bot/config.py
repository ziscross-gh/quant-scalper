"""
Configuration Management

Loads and validates bot configuration from YAML file.
"""
import os
import yaml
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


@dataclass
class StrategyConfig:
    """Strategy parameters"""
    lookback_period: int = 20
    z_threshold_entry: float = 2.0
    z_threshold_exit: float = 0.5
    min_volume: int = 100


@dataclass
class RiskConfig:
    """Risk management parameters"""
    max_position_size: int = 2
    stop_loss_dollars: float = 200.0
    take_profit_dollars: float = 300.0
    max_daily_loss: float = 500.0
    max_consecutive_losses: int = 3
    max_position_duration_hours: float = 2.0


@dataclass
class IBKRConfig:
    """IBKR connection parameters"""
    host: str = "127.0.0.1"
    port: int = 4002
    client_id: int = 1
    account: str = ""
    paper: bool = True
    reconnect_delay: int = 10
    max_reconnect_attempts: int = 5


@dataclass
class InstrumentConfig:
    """Trading instrument configuration"""
    symbol: str
    exchange: str
    sec_type: str
    expiry: str
    multiplier: float = 5.0
    tick_size: float = 0.25
    tick_value: float = 1.25


@dataclass
class TelegramConfig:
    """Telegram alert configuration"""
    enabled: bool = False
    bot_token: str = ""
    chat_id: str = ""


@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str = "INFO"
    file: str = "logs/bot.log"
    max_size_mb: int = 10
    backup_count: int = 5


@dataclass
class DatabaseConfig:
    """Database configuration"""
    url: str = "sqlite:///data/trades.db"
    echo: bool = False


@dataclass
class TradingHoursConfig:
    """Trading hours configuration"""
    start: str = "09:30"
    end: str = "16:00"
    timezone: str = "America/New_York"
    days: List[int] = (0, 1, 2, 3, 4)  # Monday=0 through Friday=4


@dataclass
class DebugConfig:
    """Debug options"""
    dry_run: bool = False
    log_all_bars: bool = False
    save_market_data: bool = False


@dataclass
class Config:
    """Complete bot configuration"""
    strategy: StrategyConfig
    risk: RiskConfig
    ibkr: IBKRConfig
    instruments: List[InstrumentConfig]
    alerts: Dict[str, Any]
    logging: LoggingConfig
    database: DatabaseConfig
    trading_hours: TradingHoursConfig
    debug: DebugConfig

    @property
    def telegram(self) -> TelegramConfig:
        """Get Telegram config from alerts dict"""
        telegram_cfg = self.alerts.get("telegram", {})
        return TelegramConfig(
            enabled=telegram_cfg.get("enabled", False),
            bot_token=self._expand_env(telegram_cfg.get("bot_token", "")),
            chat_id=self._expand_env(telegram_cfg.get("chat_id", "")),
        )

    @staticmethod
    def _expand_env(value: str) -> str:
        """Expand environment variables in config values"""
        if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
            var_name = value[2:-1]
            return os.environ.get(var_name, "")
        return value

    @classmethod
    def load(cls, config_path: str) -> "Config":
        """Load configuration from YAML file"""
        logger.info(f"Loading config from {config_path}")

        if not Path(config_path).exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(config_path, "r") as f:
            data = yaml.safe_load(f)

        # Parse and validate
        return cls(
            strategy=StrategyConfig(**data.get("strategy", {})),
            risk=RiskConfig(**data.get("risk", {})),
            ibkr=IBKRConfig(**data.get("ibkr", {})),
            instruments=[
                InstrumentConfig(**inst)
                for inst in data.get("instruments", [])
            ],
            alerts=data.get("alerts", {}),
            logging=LoggingConfig(**data.get("logging", {})),
            database=DatabaseConfig(**data.get("database", {})),
            trading_hours=TradingHoursConfig(**data.get("trading_hours", {})),
            debug=DebugConfig(**data.get("debug", {})),
        )

    def validate(self) -> List[str]:
        """Validate configuration and return any errors"""
        errors = []

        # IBKR config
        if not self.ibkr.account:
            errors.append("IBKR account ID is required")

        # Telegram
        if self.telegram.enabled:
            if not self.telegram.bot_token:
                errors.append("Telegram bot_token is required when enabled")
            if not self.telegram.chat_id:
                errors.append("Telegram chat_id is required when enabled")

        # Instruments
        if not self.instruments:
            errors.append("At least one instrument must be configured")

        # Safety check
        if not self.ibkr.paper:
            logger.warning("⚠️ LIVE TRADING MODE ENABLED - BE CAREFUL!")

        return errors


if __name__ == "__main__":
    # Test config loading
    try:
        config = Config.load("config/config.yaml.example")
        print("✅ Config loaded successfully")
        print(f"Strategy lookback: {config.strategy.lookback_period}")
        print(f"Risk max daily loss: ${config.risk.max_daily_loss}")
        print(f"IBKR paper mode: {config.ibkr.paper}")

        errors = config.validate()
        if errors:
            print("\nValidation errors:")
            for error in errors:
                print(f"  ❌ {error}")
        else:
            print("\n✅ Config is valid")
    except Exception as e:
        print(f"❌ Error: {e}")
