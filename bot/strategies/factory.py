# Strategy Framework
from enum import Enum
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class StrategyType(Enum):
    """Available strategy types."""
    ZSCORE_MEAN_REVERSION = "zscore_mean_reversion"
    BOLLINGER_BANDS = "bollinger_bands"
    RSI_MEAN_REVERSION = "rsi_mean_reversion"
    MA_CROSSOVER = "ma_crossover"


class TradingStrategy(ABC):
    """Base class for trading strategies."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.position = 0  # LONG, SHORT, or FLAT

    @abstractmethod
    def update(self, bar: Dict[str, Any]) -> Optional[str]:
        """
        Update strategy with new bar and generate signal.

        Args:
            bar: Market data bar with OHLCV

        Returns:
            Signal type or None: "ENTER_LONG", "ENTER_SHORT", "EXIT", or None
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Get strategy display name."""
        pass

    @abstractmethod
    def get_params(self) -> Dict[str, Any]:
        """Get current strategy parameters."""
        pass


class ZScoreMeanReversion(TradingStrategy):
    """Z-Score mean reversion strategy."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.lookback = config.get("lookback", 20)
        self.z_entry = config.get("z_threshold_entry", 2.0)
        self.z_exit = config.get("z_threshold_exit", 0.5)

        # Z-Score engine
        from bot.core.signals import SignalGenerator
        self.signal_gen = SignalGenerator(self.lookback)

    def update(self, bar: Dict[str, Any]) -> Optional[str]:
        """Update and generate signal."""
        price = bar.get("close", 0.0)
        zscore = self.signal_gen.update(price)

        if not self.signal_gen.is_ready():
            return None

        signal = self.signal_gen.get_signal(
            z_threshold_entry=self.z_entry,
            z_threshold_exit=self.z_exit,
        )

        if signal:
            return signal["type"]
        return None

    def get_name(self) -> str:
        return "Z-Score Mean Reversion"

    def get_params(self) -> Dict[str, Any]:
        return {
            "lookback": self.lookback,
            "z_threshold_entry": self.z_entry,
            "z_threshold_exit": self.z_exit,
        }


class BollingerBands(TradingStrategy):
    """Bollinger Bands strategy."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.lookback = config.get("lookback", 20)
        self.std_dev = config.get("std_dev_multiplier", 2.0)

        # Price history for bands
        self.prices = []

    def update(self, bar: Dict[str, Any]) -> Optional[str]:
        """Update and generate signal."""
        price = bar.get("close", 0.0)
        self.prices.append(price)

        # Keep only lookback period
        if len(self.prices) > self.lookback:
            self.prices.pop(0)

        if len(self.prices) < self.lookback:
            return None

        # Calculate bands
        import statistics
        mean = statistics.mean(self.prices)
        std = statistics.stdev(self.prices)

        upper_band = mean + self.std_dev * std
        lower_band = mean - self.std_dev * std
        middle_band = mean

        # Generate signals
        if self.position == 0:  # No position
            if price >= upper_band:
                self.position = -1
                return "ENTER_SHORT"
            elif price <= lower_band:
                self.position = 1
                return "ENTER_LONG"
        elif self.position > 0:  # Long position
            if price <= middle_band or price >= upper_band:
                self.position = 0
                return "EXIT"
        elif self.position < 0:  # Short position
            if price >= middle_band or price <= lower_band:
                self.position = 0
                return "EXIT"

        return None

    def get_name(self) -> str:
        return "Bollinger Bands"

    def get_params(self) -> Dict[str, Any]:
        return {
            "lookback": self.lookback,
            "std_dev_multiplier": self.std_dev,
        }


class RSIMeanReversion(TradingStrategy):
    """RSI mean reversion strategy."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.lookback = config.get("lookback", 14)
        self.rsi_overbought = config.get("rsi_overbought", 70)
        self.rsi_oversold = config.get("rsi_oversold", 30)

        # Price history
        self.prices = []

    def _calculate_rsi(self) -> Optional[float]:
        """Calculate RSI."""
        if len(self.prices) < self.lookback + 1:
            return None

        gains = []
        losses = []

        for i in range(1, len(self.prices)):
            change = self.prices[i] - self.prices[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))

        if not gains:
            return 50.0

        avg_gain = sum(gains[-self.lookback:]) / self.lookback
        avg_loss = sum(losses[-self.lookback:]) / self.lookback

        rs = avg_gain / avg_loss if avg_loss > 0 else 0

        rsi = 100 - (100 / (1 + rs))
        return rsi

    def update(self, bar: Dict[str, Any]) -> Optional[str]:
        """Update and generate signal."""
        price = bar.get("close", 0.0)
        self.prices.append(price)

        if len(self.prices) > self.lookback + 50:
            self.prices = self.prices[-(self.lookback + 50):]

        rsi = self._calculate_rsi()

        if rsi is None:
            return None

        # Generate signals
        if self.position == 0:
            if rsi <= self.rsi_oversold:
                self.position = 1
                return "ENTER_LONG"
            elif rsi >= self.rsi_overbought:
                self.position = -1
                return "ENTER_SHORT"
        elif self.position > 0:
            if rsi >= 50:
                self.position = 0
                return "EXIT"
        elif self.position < 0:
            if rsi <= 50:
                self.position = 0
                return "EXIT"

        return None

    def get_name(self) -> str:
        return "RSI Mean Reversion"

    def get_params(self) -> Dict[str, Any]:
        return {
            "lookback": self.lookback,
            "rsi_overbought": self.rsi_overbought,
            "rsi_oversold": self.rsi_oversold,
        }


def create_strategy(
    strategy_type: StrategyType,
    config: Dict[str, Any],
) -> TradingStrategy:
    """
    Create a strategy instance.

    Args:
        strategy_type: Type of strategy to create
        config: Strategy configuration

    Returns:
        Strategy instance
    """
    if strategy_type == StrategyType.ZSCORE_MEAN_REVERSION:
        return ZScoreMeanReversion(config)
    elif strategy_type == StrategyType.BOLLINGER_BANDS:
        return BollingerBands(config)
    elif strategy_type == StrategyType.RSI_MEAN_REVERSION:
        return RSIMeanReversion(config)
    else:
        raise ValueError(f"Unknown strategy type: {strategy_type}")


def list_strategies() -> Dict[str, StrategyType]:
    """List available strategies."""
    return {
        "zscore": StrategyType.ZSCORE_MEAN_REVERSION,
        "bollinger": StrategyType.BOLLINGER_BANDS,
        "rsi": StrategyType.RSI_MEAN_REVERSION,
    }


def test_strategies():
    """Test all strategies."""
    print("Testing Multiple Strategies")
    print("=" * 60)
    print()

    strategies = list_strategies()

    for name, stype in strategies.items():
        config = {
            "lookback": 20,
            "z_threshold_entry": 2.0,
            "z_threshold_exit": 0.5,
            "std_dev_multiplier": 2.0,
            "rsi_overbought": 70,
            "rsi_oversold": 30,
        }

        strategy = create_strategy(stype, config)
        print(f"{strategy.get_name()}: OK")
        print(f"  Parameters: {strategy.get_params()}")
        print()

    print("✅ Strategies test complete!")


if __name__ == "__main__":
    test_strategies()
