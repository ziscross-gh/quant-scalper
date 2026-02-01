# Market data generation
from .simulator import (
    Bar,
    generate_realistic_bars,
    generate_bullish_bars,
    generate_bearish_bars,
    generate_sideways_bars,
    generate_regime_switching_bars,
)

__all__ = [
    "Bar",
    "generate_realistic_bars",
    "generate_bullish_bars",
    "generate_bearish_bars",
    "generate_sideways_bars",
    "generate_regime_switching_bars",
]
