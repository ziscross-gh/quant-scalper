"""
Pytest configuration and shared fixtures for all tests.
"""
import pytest
import tempfile
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from bot.config import (
    Config, TradingConfig, IBKRConfig, RiskConfig,
    TelegramConfig, DatabaseConfig, DebugConfig
)


@pytest.fixture
def temp_dir():
    """Create temporary directory for test files"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_config_dict() -> Dict[str, Any]:
    """Sample configuration dictionary for testing"""
    return {
        "trading": {
            "symbol": "MES",
            "exchange": "GLOBEX",
            "currency": "USD",
            "lookback_bars": 20,
            "z_entry_threshold": 2.0,
            "z_exit_threshold": 0.5,
            "min_volume_filter": 100
        },
        "ibkr": {
            "host": "127.0.0.1",
            "port": 4002,
            "client_id": 1,
            "account": "DU12345",
            "timeout_seconds": 30
        },
        "risk": {
            "max_daily_loss": 500.0,
            "max_position_size": 2,
            "max_consecutive_losses": 3,
            "max_trades_per_day": 10,
            "position_timeout_hours": 2.0,
            "drawdown_limit_percent": 10.0,
            "cooldown_minutes": 30
        },
        "telegram": {
            "enabled": False,
            "bot_token": "test-token",
            "chat_id": "test-chat"
        },
        "database": {
            "path": "data/test_trades.db"
        },
        "debug": {
            "dry_run": True,
            "log_level": "INFO"
        }
    }


@pytest.fixture
def sample_config(sample_config_dict, temp_dir) -> Config:
    """Create sample Config object for testing"""
    # Update database path to use temp directory
    sample_config_dict["database"]["path"] = str(temp_dir / "trades.db")

    return Config(
        trading=TradingConfig(**sample_config_dict["trading"]),
        ibkr=IBKRConfig(**sample_config_dict["ibkr"]),
        risk=RiskConfig(**sample_config_dict["risk"]),
        telegram=TelegramConfig(**sample_config_dict["telegram"]),
        database=DatabaseConfig(**sample_config_dict["database"]),
        debug=DebugConfig(**sample_config_dict["debug"])
    )


@pytest.fixture
def config_yaml_file(sample_config_dict, temp_dir) -> Path:
    """Create temporary YAML config file"""
    import yaml

    config_path = temp_dir / "test_config.yaml"
    with open(config_path, 'w') as f:
        yaml.dump(sample_config_dict, f)

    return config_path


@pytest.fixture
def mock_price_bars():
    """Generate sample price bars for testing"""
    base_price = 5000.0
    bars = []

    # Generate 30 bars with some variation
    for i in range(30):
        price = base_price + (i * 0.5) - 7.5  # Slight uptrend
        bars.append({
            "time": datetime.now(timezone.utc),
            "open": price - 0.25,
            "high": price + 0.5,
            "low": price - 0.5,
            "close": price,
            "volume": 1000 + (i * 10)
        })

    return bars


@pytest.fixture
def mock_zscore_engine():
    """Mock ZScoreEngine for testing without Rust dependency"""
    class MockZScoreEngine:
        def __init__(self, lookback: int):
            self.lookback = lookback
            self.prices = []

        def update(self, price: float) -> float:
            self.prices.append(price)
            if len(self.prices) < self.lookback:
                return None

            # Simple mock Z-Score calculation
            recent = self.prices[-self.lookback:]
            mean = sum(recent) / len(recent)
            variance = sum((x - mean) ** 2 for x in recent) / (len(recent) - 1)
            std = variance ** 0.5

            if std < 1e-10:
                return 0.0

            return (price - mean) / std

        def reset(self):
            self.prices = []

        def is_ready(self) -> bool:
            return len(self.prices) >= self.lookback

        def get_mean(self) -> float:
            if len(self.prices) < self.lookback:
                return None
            recent = self.prices[-self.lookback:]
            return sum(recent) / len(recent)

        def get_std(self) -> float:
            if len(self.prices) < self.lookback:
                return None
            recent = self.prices[-self.lookback:]
            mean = sum(recent) / len(recent)
            variance = sum((x - mean) ** 2 for x in recent) / (len(recent) - 1)
            return variance ** 0.5

    return MockZScoreEngine


@pytest.fixture
def mock_risk_calculator():
    """Mock RiskCalculator for testing without Rust dependency"""
    class MockRiskCalculator:
        def __init__(self, max_daily_loss: float):
            self.max_daily_loss = max_daily_loss
            self.realized_pnl = 0.0
            self.positions = {}

        def update_position(self, symbol: str, quantity: int, entry_price: float,
                          multiplier: float, entry_time: float = None):
            if quantity == 0:
                self.positions.pop(symbol, None)
            else:
                self.positions[symbol] = {
                    "quantity": quantity,
                    "entry_price": entry_price,
                    "current_price": entry_price,
                    "multiplier": multiplier,
                    "entry_time": entry_time
                }

        def update_price(self, symbol: str, price: float):
            if symbol in self.positions:
                self.positions[symbol]["current_price"] = price

        def add_realized_pnl(self, pnl: float):
            self.realized_pnl += pnl

        def unrealized_pnl(self) -> float:
            total = 0.0
            for pos in self.positions.values():
                pnl = (pos["current_price"] - pos["entry_price"]) * pos["quantity"] * pos["multiplier"]
                total += pnl
            return total

        def get_realized_pnl(self) -> float:
            return self.realized_pnl

        def total_pnl(self) -> float:
            return self.realized_pnl + self.unrealized_pnl()

        def is_daily_loss_breached(self) -> bool:
            return self.total_pnl() <= -self.max_daily_loss

        def remaining_risk(self) -> float:
            return self.max_daily_loss + self.total_pnl()

        def has_position(self, symbol: str) -> bool:
            return symbol in self.positions

        def get_quantity(self, symbol: str) -> int:
            return self.positions.get(symbol, {}).get("quantity", 0)

        def reset_daily(self):
            self.realized_pnl = 0.0

        def clear_positions(self):
            self.positions = {}

    return MockRiskCalculator


@pytest.fixture
def mock_ibkr_client():
    """Mock IBKR client for testing"""
    class MockIBKRClient:
        def __init__(self):
            self.connected = False
            self.orders = []
            self.positions = {}
            self.market_data = {}

        async def connect(self):
            self.connected = True

        async def disconnect(self):
            self.connected = False

        def is_connected(self) -> bool:
            return self.connected

        async def subscribe_market_data(self, contract, callback):
            self.market_data[contract.symbol] = callback

        async def place_order(self, contract, action: str, quantity: int):
            order_id = len(self.orders) + 1
            self.orders.append({
                "id": order_id,
                "symbol": contract.symbol,
                "action": action,
                "quantity": quantity,
                "status": "Filled"
            })
            return order_id

        def get_positions(self):
            return self.positions

    return MockIBKRClient


@pytest.fixture
def mock_telegram_alerts():
    """Mock Telegram alerts for testing"""
    class MockTelegramAlerts:
        def __init__(self):
            self.messages = []

        def send(self, text: str, parse_mode: str = "HTML"):
            self.messages.append({
                "text": text,
                "parse_mode": parse_mode,
                "timestamp": datetime.now(timezone.utc)
            })

        async def start(self):
            pass

        async def stop(self):
            pass

        def get_messages(self):
            return self.messages

        def clear(self):
            self.messages = []

    return MockTelegramAlerts
