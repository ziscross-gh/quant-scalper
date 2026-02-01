#!/usr/bin/env python3
"""
Generate volatile test data for backtesting.

Creates more realistic price action with mean reversion.
"""
import sys
sys.path.insert(0, '.')

from bot.backtest import generate_test_bars, Bar, BacktestEngine
from bot.config import Config


def generate_volatile_bars(days: int = 30) -> list:
    """
    Generate bars with more volatility to trigger more trades.

    Args:
        days: Number of days

    Returns:
        List of Bar objects
    """
    import random
    from datetime import datetime, timedelta

    bars = []
    current_time = datetime.utcnow() - timedelta(days=days)

    price = 5000.0
    trend = 0.0

    for i in range(days * 78):  # 78 bars per day (5-min)
        # Random volatility burst
        volatility_burst = 0.0
        if random.random() < 0.05:  # 5% chance of volatility spike
            volatility_burst = random.choice([-1, 1]) * random.uniform(2, 5)

        # Mean reversion strength
        mean_reversion = (5000.0 - price) * 0.1

        # Update price
        noise = random.gauss(0, 0.8)
        trend += random.gauss(0, 0.02)
        trend *= 0.98  # Decay trend

        price = price + noise + mean_reversion + volatility_burst + trend

        # Ensure price stays positive
        price = max(price, 4800.0)
        price = min(price, 5200.0)

        # Create OHLC
        high = price + abs(random.gauss(0, 0.5))
        low = price - abs(random.gauss(0, 0.5))
        close = price
        open_price = price - (random.gauss(0, 0.5))

        bar = Bar(
            timestamp=current_time,
            open=open_price,
            high=high,
            low=low,
            close=close,
            volume=random.randint(100, 800),
        )

        bars.append(bar)
        current_time += timedelta(minutes=5)

    return bars


def test_volatile():
    """Test backtest with volatile data"""
    print("Testing with volatile data...")
    print("=" * 60)

    config = Config.load('config/config.yaml.example')

    # Generate volatile data
    bars = generate_volatile_bars(days=30)
    print(f"Generated {len(bars)} volatile bars\n")

    # Run backtest
    engine = BacktestEngine(config)
    result = engine.run(bars=bars, multiplier=5.0, slippage=0.25)

    # Print report
    from bot.backtest import print_backtest_report
    print_backtest_report(result)

    print("✅ Volatile data test complete!")


if __name__ == "__main__":
    test_volatile()
