"""
Signal Generation

Generates trading signals based on Z-Score mean reversion strategy.
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any
import logging

# Try to import Rust engine, fall back to Python
try:
    from quant_scalper_rust import ZScoreEngine as RustZScoreEngine
    RUST_AVAILABLE = True
except ImportError:
    RUST_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class TradingSignal:
    """A trading signal"""
    type: str  # "ENTER_LONG", "ENTER_SHORT", "EXIT"
    zscore: float
    reason: str
    timestamp: float


class SignalGenerator:
    """Generates trading signals from price data"""

    def __init__(self, lookback_period: int = 20):
        self.lookback_period = lookback_period

        # Use Rust engine if available, otherwise Python
        if RUST_AVAILABLE:
            logger.info("Using Rust Z-Score engine (high performance)")
            self.engine = RustZScoreEngine(lookback_period)
        else:
            logger.warning("Rust engine not available, using Python fallback")
            self.engine = PythonZScoreEngine(lookback_period)

        self._last_signal_type: Optional[str] = None

    def update(self, price: float) -> Optional[float]:
        """
        Update with new price and return current Z-Score.

        Args:
            price: Current market price

        Returns:
            Current Z-Score, or None if not enough data yet
        """
        return self.engine.update(price)

    def is_ready(self) -> bool:
        """Check if the engine has enough data to generate signals"""
        return self.engine.is_ready()

    def get_mean(self) -> Optional[float]:
        """Get current rolling mean"""
        return self.engine.get_mean()

    def get_std(self) -> Optional[float]:
        """Get current rolling standard deviation"""
        return self.engine.get_std()

    def get_signal(
        self,
        z_threshold_entry: float = 2.0,
        z_threshold_exit: float = 0.5,
    ) -> Optional[Dict[str, Any]]:
        """
        Generate a trading signal based on current Z-Score.

        Strategy:
        - If Z ≥ +threshold_entry: Enter SHORT (overextended)
        - If Z ≤ -threshold_entry: Enter LONG (oversold)
        - If position is open and |Z| ≤ threshold_exit: EXIT

        Args:
            z_threshold_entry: Z-Score threshold for entry (default: 2.0)
            z_threshold_exit: Z-Score threshold for exit (default: 0.5)

        Returns:
            Signal dict with type and reason, or None if no signal
        """
        zscore = self.engine.get_zscore()

        if zscore is None:
            return None

        signal = None

        # Entry signals
        if zscore >= z_threshold_entry:
            if self._last_signal_type not in ["ENTER_SHORT", None]:
                signal = {
                    "type": "ENTER_SHORT",
                    "zscore": zscore,
                    "reason": f"Z-Score ({zscore:.2f}) ≥ +{z_threshold_entry}",
                }
                self._last_signal_type = "ENTER_SHORT"

        elif zscore <= -z_threshold_entry:
            if self._last_signal_type not in ["ENTER_LONG", None]:
                signal = {
                    "type": "ENTER_LONG",
                    "zscore": zscore,
                    "reason": f"Z-Score ({zscore:.2f}) ≤ -{z_threshold_entry}",
                }
                self._last_signal_type = "ENTER_LONG"

        # Exit signal
        elif abs(zscore) <= z_threshold_exit and self._last_signal_type in ["ENTER_LONG", "ENTER_SHORT"]:
            signal = {
                "type": "EXIT",
                "zscore": zscore,
                "reason": f"Z-Score ({zscore:.2f}) returned to mean",
            }
            self._last_signal_type = None

        return signal


class PythonZScoreEngine:
    """Python fallback Z-Score engine (for when Rust is not available)"""

    def __init__(self, period: int):
        self.period = period
        self.prices: list[float] = []
        self._zscore: Optional[float] = None

    def update(self, price: float) -> Optional[float]:
        """Update with new price"""
        self.prices.append(price)

        # Keep only last N prices
        if len(self.prices) > self.period:
            self.prices.pop(0)

        # Calculate Z-Score
        if len(self.prices) >= self.period:
            mean = sum(self.prices) / len(self.prices)
            variance = sum((p - mean) ** 2 for p in self.prices) / len(self.prices)
            std = variance ** 0.5

            if std > 0:
                self._zscore = (price - mean) / std
            else:
                self._zscore = 0.0
        else:
            self._zscore = None

        return self._zscore

    def is_ready(self) -> bool:
        """Check if we have enough data"""
        return len(self.prices) >= self.period

    def get_zscore(self) -> Optional[float]:
        """Get current Z-Score"""
        return self._zscore

    def get_mean(self) -> Optional[float]:
        """Get current mean"""
        if not self.prices:
            return None
        return sum(self.prices) / len(self.prices)

    def get_std(self) -> Optional[float]:
        """Get current standard deviation"""
        if not self.prices:
            return None
        mean = sum(self.prices) / len(self.prices)
        variance = sum((p - mean) ** 2 for p in self.prices) / len(self.prices)
        return variance ** 0.5


if __name__ == "__main__":
    import time

    def test():
        """Test signal generation"""
        gen = SignalGenerator(lookback_period=20)

        print("Testing signal generator...")
        print("=" * 50)

        # Generate price series with mean reversion
        import random
        price = 100.0
        for i in range(50):
            # Random walk with slight mean reversion
            change = random.gauss(0, 0.5)
            if i > 20:
                # Add some mean reversion after warming up
                change -= (price - 100.0) * 0.1
            price += change

            zscore = gen.update(price)

            if gen.is_ready():
                signal = gen.get_signal(z_threshold_entry=2.0, z_threshold_exit=0.5)

                if signal:
                    emoji = {"ENTER_LONG": "📈", "ENTER_SHORT": "📉", "EXIT": "✅"}
                    print(f"{emoji[signal['type']]} Bar {i+1}: {signal['type']} | Z={zscore:.2f} | Price={price:.2f}")
                    print(f"   Reason: {signal['reason']}")
            elif i % 10 == 0:
                print(f"⏳ Bar {i+1}: Warming up... | Price={price:.2f}")

        print("=" * 50)
        print(f"Final Z-Score: {gen.engine.get_zscore():.2f}")
        print(f"Mean: {gen.get_mean():.2f}")
        print(f"Std Dev: {gen.get_std():.2f}")
        print(f"Rust engine: {'✅ Available' if RUST_AVAILABLE else '❌ Not available'}")

    test()
