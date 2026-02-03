# Backtest engine for strategy optimization
# ============================================================================

"""
Backtest engine for strategy optimization and performance metrics.

Fixed: Now correctly exports all market data generators including
generate_test_bars_with_volatility() from bot.market_data.simulator.
"""
from .engine import BacktestEngine, BacktestResult, Bar
from .walkforward import WalkForwardAnalyzer, WalkForwardResult
from ..market_data.simulator import (
    generate_test_bars,
    generate_test_bars_with_volatility,
    generate_bullish_bars,
    generate_bearish_bars,
    generate_sideways_bars,
    generate_regime_switching_bars,
)

__all__ = [
    "BacktestEngine",
    "BacktestResult",
    "Bar",
    "generate_test_bars",
    "generate_test_bars_with_volatility",
    "generate_bullish_bars",
    "generate_bearish_bars",
    "generate_sideways_bars",
    "generate_regime_switching_bars",
    "WalkForwardAnalyzer",
    "WalkForwardResult",
    "print_backtest_report",
]
