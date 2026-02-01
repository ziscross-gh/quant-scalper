#!/usr/bin/env python3
"""
Parameter optimization using backtest engine.

Tests multiple parameter combinations to find optimal settings.
"""
import sys
sys.path.insert(0, '.')

import itertools
from bot.config import Config
from bot.backtest import BacktestEngine, generate_test_bars, print_backtest_report
from bot.backtest.engine import BacktestResult, Bar


def optimize_parameters(
    config_path: str = 'config/config.yaml.example',
    lookback_range: list = [15, 20, 25, 30],
    z_entry_range: list = [1.5, 2.0, 2.5, 3.0],
    z_exit_range: list = [0.3, 0.5, 0.7],
    top_n: int = 5,
) -> list:
    """
    Run parameter optimization.

    Args:
        config_path: Path to config file
        lookback_range: List of lookback periods to test
        z_entry_range: List of entry Z-score thresholds to test
        z_exit_range: List of exit Z-score thresholds to test
        top_n: Number of best results to return

    Returns:
        List of (score, params, result) tuples, sorted by score
    """
    print("=" * 60)
    print("PARAMETER OPTIMIZATION")
    print("=" * 60)
    print()

    # Generate test data once (for fair comparison)
    print("Generating test data...")
    bars = generate_test_bars(days=60, bars_per_day=78)  # 60 days
    print(f"Generated {len(bars)} bars\n")

    # Calculate total combinations
    total_combinations = (
        len(lookback_range) *
        len(z_entry_range) *
        len(z_exit_range)
    )
    print(f"Testing {total_combinations} parameter combinations...")
    print()

    results = []
    combinations = 0

    # Iterate through all combinations
    for lookback, z_entry, z_exit in itertools.product(
        lookback_range, z_entry_range, z_exit_range
    ):
        combinations += 1
        print(f"\r[{combinations}/{total_combinations}] Testing...", end='', flush=True)

        # Create config with these parameters
        config = Config.load(config_path)
        config.strategy.lookback_period = lookback
        config.strategy.z_threshold_entry = z_entry
        config.strategy.z_threshold_exit = z_exit

        # Run backtest
        engine = BacktestEngine(config)
        result = engine.run(bars=bars, multiplier=5.0, slippage=0.25)

        # Calculate score (weighted combination of metrics)
        # Higher score is better
        score = calculate_score(result)

        params = {
            "lookback": lookback,
            "z_entry": z_entry,
            "z_exit": z_exit,
        }

        results.append((score, params, result))

    print()  # Newline after progress
    print()

    # Sort by score (descending)
    results.sort(key=lambda x: x[0], reverse=True)

    # Print top N results
    print("=" * 60)
    print(f"TOP {top_n} PARAMETER SETS")
    print("=" * 60)
    print()

    for i, (score, params, result) in enumerate(results[:top_n], 1):
        print(f"🏆 #{i}")
        print("-" * 60)
        print(f"  Score:           {score:.2f}")
        print(f"  Lookback:        {params['lookback']} bars")
        print(f"  Z-Entry:         ±{params['z_entry']}")
        print(f"  Z-Exit:          ±{params['z_exit']}")
        print()
        print(f"  Trades:          {result.total_trades}")
        print(f"  Win Rate:        {result.win_rate:.1f}%")
        print(f"  Total P&L:       ${result.total_pnl:,.2f}")
        print(f"  Profit Factor:    {result.profit_factor:.2f}")
        print(f"  Max Drawdown:    ${result.max_drawdown:,.2f}")
        print(f"  Sharpe Ratio:    {result.sharpe_ratio:.2f}")
        print()

    return results[:top_n]


def calculate_score(result: BacktestResult) -> float:
    """
    Calculate a single score for backtest result.

    Weights:
    - Profit Factor: 40% (most important)
    - Win Rate: 25%
    - Sharpe Ratio: 20%
    - Max Drawdown (penalty): 15%

    Returns:
        Score (higher is better)
    """
    # Normalize metrics to 0-1 range
    profit_factor_score = min(result.profit_factor / 2.0, 1.0)  # 2.0 is excellent
    win_rate_score = result.win_rate / 60.0  # 60% is excellent
    sharpe_score = min((result.sharpe_ratio + 2) / 4.0, 1.0)  # 2.0 is excellent
    drawdown_penalty = min(result.max_drawdown / 1000.0, 1.0)  # $1000 drawdown

    # Weighted combination
    score = (
        profit_factor_score * 0.40 +
        win_rate_score * 0.25 +
        sharpe_score * 0.20 +
        (1.0 - drawdown_penalty) * 0.15
    )

    return score * 100  # Scale to 0-100


def print_comparison(results: list):
    """Print side-by-side comparison of top results"""
    print()
    print("=" * 100)
    print("PARAMETER COMPARISON TABLE")
    print("=" * 100)
    print()
    print(f"{'Rank':<6} {'Lookback':<10} {'Z-Entry':<10} {'Z-Exit':<10} "
          f"{'Trades':<8} {'Win%':<8} {'P&L':<12} {'PF':<6} {'DD':<10} {'Sharpe':<8}")
    print("-" * 100)

    for i, (score, params, result) in enumerate(results, 1):
        print(f"{i:<6} {params['lookback']:<10} "
              f"{params['z_entry']:<10} {params['z_exit']:<10} "
              f"{result.total_trades:<8} {result.win_rate:<7.1f}% "
              f"${result.total_pnl:>9,.2f} "
              f"{result.profit_factor:<6.2f} "
              f"${result.max_drawdown:>8,.0f} "
              f"{result.sharpe_ratio:<8.2f}")

    print()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Optimize backtest parameters")
    parser.add_argument("--config", default="config/config.yaml.example",
                       help="Path to config file")
    parser.add_argument("--top", type=int, default=5,
                       help="Number of top results to show")
    parser.add_argument("--quick", action="store_true",
                       help="Quick test with fewer combinations")

    args = parser.parse_args()

    if args.quick:
        lookback_range = [20]
        z_entry_range = [1.5, 2.0, 2.5]
        z_exit_range = [0.3, 0.5]
    else:
        lookback_range = [15, 20, 25, 30]
        z_entry_range = [1.5, 2.0, 2.5, 3.0]
        z_exit_range = [0.3, 0.5, 0.7]

    results = optimize_parameters(
        config_path=args.config,
        lookback_range=lookback_range,
        z_entry_range=z_entry_range,
        z_exit_range=z_exit_range,
        top_n=args.top,
    )

    # Print comparison table
    print_comparison(results[:args.top])

    print("✅ Optimization complete!")
