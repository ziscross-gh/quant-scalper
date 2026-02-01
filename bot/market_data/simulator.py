# Market Data Simulator
# Generates realistic market data with complex patterns.

import random
from datetime import datetime, timedelta
from typing import List
from dataclasses import dataclass


@dataclass
class Bar:
    """OHLCV bar"""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


def generate_realistic_bars(
    days: int = 30,
    bars_per_day: int = 78,
    base_price: float = 5000.0,
    volatility: float = 0.5,
    trend_strength: float = 0.02,
    mean_reversion: float = 0.1,
    volatility_cluster_prob: float = 0.05,
) -> List[Bar]:
    """
    Generate realistic market data with complex patterns.

    Features:
    - Mean reversion
    - Volatility clustering
    - Trend with decay
    - Price gaps
    - Liquidity variation

    Args:
        days: Number of days
        bars_per_day: Bars per day (5-minute bars = 78)
        base_price: Starting price
        volatility: Base volatility
        trend_strength: Trend persistence
        mean_reversion: Pull toward base price
        volatility_cluster_prob: Probability of volatility spike

    Returns:
        List of realistic bars
    """
    bars = []
    current_time = datetime.utcnow() - timedelta(days=days)

    price = base_price
    trend = 0.0
    current_volatility = volatility
    cluster_duration = 0

    for i in range(days * bars_per_day):
        # Volatility clustering
        if random.random() < volatility_cluster_prob:
            current_volatility = volatility * random.uniform(2.0, 4.0)
            # Volatility clusters persist for 10-30 bars
            cluster_duration = random.randint(10, 30)
        elif cluster_duration > 0:
            cluster_duration -= 1
        else:
            current_volatility = volatility

        # Mean reversion
        reversion = (base_price - price) * mean_reversion

        # Trend
        trend += random.gauss(0, 0.01)
        trend *= 0.99  # Decay

        # Noise
        noise = random.gauss(0, current_volatility)

        # Price gaps (rare)
        if random.random() < 0.001:  # 0.1% chance
            gap_size = random.choice([-1, 1]) * random.uniform(2.0, 5.0)
            price += gap_size

        # Update price
        price = price + noise + reversion + trend_strength * trend

        # Keep price in reasonable range
        price = max(price, base_price * 0.9)
        price = min(price, base_price * 1.1)

        # Create OHLC
        high = price + abs(random.gauss(0, 0.4))
        low = price - abs(random.gauss(0, 0.4))
        close = price
        open_price = price - (random.gauss(0, 0.5))

        # Volume variation (liquidity)
        base_volume = random.randint(100, 500)
        volume_variation = random.choice([0.5, 1.0, 1.5, 2.0])
        volume = int(base_volume * volume_variation)

        bar = Bar(
            timestamp=current_time,
            open=open_price,
            high=max(open_price, high),
            low=min(open_price, low),
            close=close,
            volume=volume,
        )

        bars.append(bar)

        # Advance time (5-minute bars)
        current_time += timedelta(minutes=5)

    return bars


def generate_bullish_bars(days: int = 30) -> List[Bar]:
    """Generate bullish market data (uptrend)."""
    return generate_realistic_bars(
        days=days,
        base_price=5000.0,
        volatility=0.4,
        trend_strength=0.05,  # Strong uptrend
        mean_reversion=0.05,  # Weak mean reversion
        volatility_cluster_prob=0.03,
    )


def generate_bearish_bars(days: int = 30) -> List[Bar]:
    """Generate bearish market data (downtrend)."""
    return generate_realistic_bars(
        days=days,
        base_price=5000.0,
        volatility=0.6,  # Higher volatility
        trend_strength=-0.05,  # Downtrend
        mean_reversion=0.05,
        volatility_cluster_prob=0.08,  # More volatility spikes
    )


def generate_sideways_bars(days: int = 30) -> List[Bar]:
    """Generate sideways/ranging market data."""
    return generate_realistic_bars(
        days=days,
        base_price=5000.0,
        volatility=0.5,
        trend_strength=0.0,  # No trend
        mean_reversion=0.15,  # Strong mean reversion
        volatility_cluster_prob=0.02,
    )


def generate_regime_switching_bars(days: int = 60) -> List[Bar]:
    """
    Generate data with regime switches.

    Simulates different market conditions:
    - Sideways -> Bullish -> Volatile -> Sideways
    """
    all_bars = []
    regimes = [
        ("Sideways", 15, generate_sideways_bars),
        ("Bullish", 15, generate_bullish_bars),
        ("Volatile", 15, generate_realistic_bars),
        ("Sideways2", 15, generate_sideways_bars),
    ]

    current_time = datetime.utcnow() - timedelta(days=days)

    for name, length, generator in regimes:
        regime_bars = generator(days=length)

        # Adjust timestamps to be continuous
        time_offset = current_time + timedelta(days=sum(
            r[1] for r in regimes[:regimes.index((name, length, generator))]
        ))

        for bar in regime_bars:
            bar.timestamp = time_offset
            time_offset += timedelta(minutes=5)
            all_bars.append(bar)

    return all_bars[:days * 78]


def test_market_simulator():
    """Test all market data generators."""
    print("Testing Market Data Simulator")
    print("=" * 60)

    # Test default realistic data
    print("\n1. Realistic (mixed) data:")
    bars = generate_realistic_bars(days=5)
    print(f"   Generated {len(bars)} bars")
    print(f"   First bar: {bars[0].timestamp} | "
          f"{bars[0].open:.2f}-{bars[0].high:.2f}-{bars[0].low:.2f}-{bars[0].close:.2f}")
    print(f"   Last bar: {bars[-1].timestamp} | "
          f"{bars[-1].open:.2f}-{bars[-1].high:.2f}-{bars[-1].low:.2f}-{bars[-1].close:.2f}")

    # Test bullish data
    print("\n2. Bullish data:")
    bull_bars = generate_bullish_bars(days=5)
    start_price = bull_bars[0].close
    end_price = bull_bars[-1].close
    change_pct = ((end_price - start_price) / start_price) * 100
    print(f"   Start: ${start_price:.2f}, End: ${end_price:.2f}")
    print(f"   Change: {change_pct:+.2f}% (should be positive)")

    # Test bearish data
    print("\n3. Bearish data:")
    bear_bars = generate_bearish_bars(days=5)
    start_price = bear_bars[0].close
    end_price = bear_bars[-1].close
    change_pct = ((end_price - start_price) / start_price) * 100
    print(f"   Start: ${start_price:.2f}, End: ${end_price:.2f}")
    print(f"   Change: {change_pct:+.2f}% (should be negative)")

    # Test sideways data
    print("\n4. Sideways data:")
    side_bars = generate_sideways_bars(days=5)
    start_price = side_bars[0].close
    end_price = side_bars[-1].close
    change_pct = ((end_price - start_price) / start_price) * 100
    print(f"   Start: ${start_price:.2f}, End: ${end_price:.2f}")
    print(f"   Change: {change_pct:+.2f}% (should be near 0%)")

    # Test regime switching
    print("\n5. Regime switching data (60 days):")
    regime_bars = generate_regime_switching_bars(days=60)
    print(f"   Generated {len(regime_bars)} bars")

    # Calculate volatility for each regime
    import statistics
    for regime in [(0, 15, "Sideways"), (15, 30, "Bullish"),
                  (30, 45, "Volatile"), (45, 60, "Sideways2")]:
        start, end, name = regime
        segment = regime_bars[start:end]
        if segment:
            returns = [
                (segment[i+1].close - segment[i].close)
                for i in range(len(segment) - 1)
            ]
            volatility = statistics.stdev(returns) if returns else 0.0
            print(f"   {name}: Volatility = {volatility:.4f}")

    print("\n✅ Market data simulator test complete!")


if __name__ == "__main__":
    test_market_simulator()
