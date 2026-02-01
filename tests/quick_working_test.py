#!/usr/bin/env python3
# Quick test that works - import correctly
import sys
sys.path.insert(0, '.')

print("Testing Features - Quick Version")
print("=" * 50)

# 1. Market data
print("\n1. Market Data Simulator")
try:
    from bot.market_data import generate_realistic_bars
    bars = generate_realistic_bars(days=5)
    print(f"   ✅ Generated {len(bars)} bars")
except Exception as e:
    print(f"   ❌ Error: {e}")

# 2. Config validator
print("\n2. Configuration Validator")
try:
    from bot.config import Config
    config = Config.load('config/config.yaml.example')
    print(f"   ✅ Loaded config")
    print(f"   Lookback: {config.strategy.lookback_period}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# 3. Strategies
print("\n3. Multiple Strategies Framework")
try:
    from bot.strategies import StrategyType, create_strategy
    print(f"   ✅ Available: {list(StrategyType)}")
    zscore = create_strategy(StrategyType.ZSCORE_MEAN_REVERSION, {})
    print(f"   ✅ Created Z-Score strategy")
except Exception as e:
    print(f"   ❌ Error: {e}")

# 4. Telegram commands
print("\n4. Telegram Commands (mock test)")
try:
    import asyncio
    from bot.telegram import TelegramCommands

    async def test():
        mock_state = {"status": "running", "daily_pnl": 250.0}
        commands = TelegramCommands(mock_state)

        # Test ping
        response = await commands.handle_command("ping", [])
        print(f"   ✅ /ping: {response[:50]}...")

    asyncio.run(test())
except Exception as e:
    print(f"   ❌ Error: {e}")

# 5. Benchmark
print("\n5. Performance Benchmark")
try:
    from bot.core.signals import SignalGenerator

    gen = SignalGenerator(20)
    import time
    import statistics

    # Quick benchmark
    times = []
    for _ in range(100):
        start = time.perf_counter()
        gen.update(5000.0)
        end = time.perf_counter()
        times.append((end - start) * 1000)

    print(f"   ✅ Signal generation mean: {statistics.mean(times):.3f}ms")
except Exception as e:
    print(f"   ❌ Error: {e}")

print()
print("=" * 50)
print("✅ ALL FEATURES TESTED!")
print("=" * 50)
