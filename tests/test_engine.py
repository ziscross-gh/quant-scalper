#!/usr/bin/env python3
"""
Test the Trading Engine with mocked components
"""
import sys
sys.path.insert(0, '.')

import asyncio
from bot.config import Config
from bot.core.engine import TradingEngine

async def test_engine():
    """Test trading engine with dry run mode"""
    print("Testing Trading Engine (Dry Run Mode)")
    print("=" * 50)

    # Load config
    config = Config.load('config/config.yaml.example')
    config.debug.dry_run = True

    # Create engine with no alerts (dry run)
    engine = TradingEngine(config, alerts=None)

    await engine.start()

    # Simulate some bars
    print("\nSimulating 25 price bars...")
    for i in range(25):
        price = 100 + i * 0.5
        bar = {"close": price}
        await engine.process_bar(bar)
        await asyncio.sleep(0.05)  # Small delay to see progress

    # Get status
    status = engine.get_status()
    print(f"\nEngine Status:")
    print(f"  Running: {status['running']}")
    print(f"  Position: {status['position']}")
    print(f"  Daily P&L: ${status['daily_pnl']:.2f}")
    print(f"  Trades today: {status['trades_today']}")
    print(f"  Z-Score: {status['zscore']}")

    # Stop engine
    await engine.stop("Test complete")

    print("\n" + "=" * 50)
    print("✅ Trading engine test passed!")

if __name__ == "__main__":
    asyncio.run(test_engine())
