"""
Walk-Forward Analysis

More realistic backtesting with training/validation splits.
"""
import sys
sys.path.insert(0, '.')

import sqlite3
import logging
from datetime import datetime
from typing import List, Dict, Any
from dataclasses import dataclass, field

from bot.config import Config
from bot.backtest import BacktestEngine, Bar, BacktestResult, print_backtest_report

logger = logging.getLogger(__name__)


@dataclass
class WalkForwardResult:
    """Results from walk-forward analysis."""
    overall_pnl: float = 0.0
    total_trades: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    folds: List[Dict[str, Any]] = field(default_factory=list)


class WalkForwardAnalyzer:
    """Walk-forward analysis engine."""

    def __init__(self, config: Config):
        self.config = config

    def run(
        self,
        bars: List[Bar],
        n_folds: int = 5,
        train_ratio: float = 0.7,
        multiplier: float = 5.0,
        slippage: float = 0.25,
    ) -> WalkForwardResult:
        """
        Run walk-forward analysis.

        Strategy:
        1. Split data into N folds
        2. For each fold:
           a. Train on first 70% (optimize parameters)
           b. Validate on next 30% (test performance)
        3. Aggregate results across all folds

        Args:
            bars: Historical bars (time-sorted)
            n_folds: Number of folds (default: 5)
            train_ratio: Portion for training (default: 0.7)
            multiplier: Contract multiplier
            slippage: Price slippage per trade

        Returns:
            WalkForwardResult with aggregated metrics
        """
        logger.info(f"Running walk-forward with {n_folds} folds...")

        result = WalkForwardResult()

        # Calculate fold size
        fold_size = len(bars) // n_folds
        train_size = int(fold_size * train_ratio)

        # Run each fold
        for fold_num in range(n_folds):
            logger.info(f"Processing fold {fold_num + 1}/{n_folds}...")

            start_idx = fold_num * fold_size
            end_idx = start_idx + fold_size

            # Split train/validate
            train_bars = bars[start_idx:start_idx + train_size]
            val_bars = bars[start_idx + train_size:end_idx]

            # Optimize on training data
            # For now, use default parameters
            # In full implementation, would run optimization here
            engine = BacktestEngine(self.config)

            # Run backtest on validation data
            fold_result = engine.run(
                bars=val_bars,
                multiplier=multiplier,
                slippage=slippage,
            )

            # Record fold results
            fold_metrics = {
                "fold": fold_num + 1,
                "train_bars": len(train_bars),
                "val_bars": len(val_bars),
                "trades": fold_result.total_trades,
                "pnl": fold_result.total_pnl,
                "win_rate": fold_result.win_rate,
                "profit_factor": fold_result.profit_factor,
                "max_drawdown": fold_result.max_drawdown,
                "sharpe_ratio": fold_result.sharpe_ratio,
            }

            result.folds.append(fold_metrics)

            # Accumulate
            result.total_trades += fold_result.total_trades
            result.overall_pnl += fold_result.total_pnl

        # Calculate overall metrics
        if result.total_trades > 0:
            # Aggregated win rate
            winning_folds = [f for f in result.folds if f["pnl"] >= 0]
            result.win_rate = len(winning_folds) / n_folds * 100

            # Aggregated profit factor
            wins = sum(f["pnl"] for f in result.folds if f["pnl"] > 0)
            losses = abs(sum(f["pnl"] for f in result.folds if f["pnl"] < 0))
            result.profit_factor = wins / losses if losses > 0 else 0.0

            # Max drawdown (worst across all folds)
            result.max_drawdown = max(f["max_drawdown"] for f in result.folds)

            # Sharpe ratio
            import statistics
            fold_returns = [f["pnl"] for f in result.folds]
            if len(fold_returns) > 1:
                mean_return = statistics.mean(fold_returns)
                std_return = statistics.stdev(fold_returns)
                result.sharpe_ratio = (
                    (mean_return / std_return) * (n_folds ** 0.5)
                    if std_return > 0 else 0.0
                )

        logger.info(f"Walk-forward complete: {result.total_trades} total trades")
        return result

    def print_report(self, result: WalkForwardResult):
        """Print walk-forward analysis report."""
        print("=" * 70)
        print("🧪 WALK-FORWARD ANALYSIS REPORT")
        print("=" * 70)
        print()

        # Overall metrics
        print("📊 Overall Performance")
        print("-" * 70)
        print(f"  Total Folds:         {len(result.folds)}")
        print(f"  Total Trades:        {result.total_trades}")
        print(f"  Winning Folds:      {sum(1 for f in result.folds if f['pnl'] >= 0)}")
        print(f"  Win Rate:           {result.win_rate:.1f}%")
        print()
        print(f"  Total P&L:          ${result.overall_pnl:,.2f}")
        print(f"  Avg P&L per Fold:   ${result.overall_pnl / len(result.folds):,.2f}")
        print(f"  Max Drawdown:        ${result.max_drawdown:,.2f}")
        print(f"  Profit Factor:       {result.profit_factor:.2f}")
        print(f"  Sharpe Ratio:        {result.sharpe_ratio:.2f}")
        print()

        # Fold-by-fold results
        print("📋 Fold-by-Fold Results")
        print("-" * 70)
        print(f"{'Fold':<6} {'Train':<8} {'Val':<6} {'Trades':<8} "
              f"{'P&L':<12} {'Win%':<6} {'PF':<6} {'Sharpe':<8}")
        print("-" * 70)

        for fold in result.folds:
            pnl_color = "🟢" if fold["pnl"] >= 0 else "🔴"
            print(
                f"#{fold['fold']:<5} {fold['train_bars']:<8} "
                f"{fold['val_bars']:<6} {fold['trades']:<8} "
                f"{pnl_color} ${fold['pnl']:>9,.2f} "
                f"{fold['win_rate']:<5.1f}% "
                f"{fold['profit_factor']:<5.2f} "
                f"{fold['sharpe_ratio']:<7.2f}"
            )

        print()

        # Interpretation
        print("📈 Interpretation")
        print("-" * 70)

        if result.win_rate >= 50:
            print("  ✅ Strategy is profitable across most folds")
        elif result.win_rate >= 40:
            print("  ⚠️  Strategy shows mixed performance")
        else:
            print("  ❌ Strategy performs poorly across folds")

        if result.profit_factor >= 1.5:
            print("  ✅ Strong risk/reward ratio")
        elif result.profit_factor >= 1.0:
            print("  ⚠️  Acceptable risk/reward ratio")
        else:
            print("  ❌ Poor risk/reward ratio")

        if result.max_drawdown < 500:
            print("  ✅ Low drawdown - conservative risk")
        elif result.max_drawdown < 1000:
            print("  ⚠️  Moderate drawdown")
        else:
            print("  ❌ High drawdown - risky strategy")

        print()
        print("=" * 70)

    def save_results(self, result: WalkForwardResult, db_path: str = "data/walkforward.db"):
        """Save walk-forward results to database."""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Create tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS walkforward_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                total_folds INTEGER,
                total_trades INTEGER,
                overall_pnl REAL,
                win_rate REAL,
                profit_factor REAL,
                max_drawdown REAL,
                sharpe_ratio REAL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS walkforward_folds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER,
                fold_num INTEGER,
                train_bars INTEGER,
                val_bars INTEGER,
                trades INTEGER,
                pnl REAL,
                win_rate REAL,
                profit_factor REAL,
                sharpe_ratio REAL,
                FOREIGN KEY (run_id) REFERENCES walkforward_runs (id)
            )
        """)

        # Insert run
        cursor.execute("""
            INSERT INTO walkforward_runs (
                timestamp, total_folds, total_trades, overall_pnl,
                win_rate, profit_factor, max_drawdown, sharpe_ratio
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.utcnow().isoformat(),
            len(result.folds),
            result.total_trades,
            result.overall_pnl,
            result.win_rate,
            result.profit_factor,
            result.max_drawdown,
            result.sharpe_ratio,
        ))

        run_id = cursor.lastrowid

        # Insert folds
        for fold in result.folds:
            cursor.execute("""
                INSERT INTO walkforward_folds (
                    run_id, fold_num, train_bars, val_bars, trades,
                    pnl, win_rate, profit_factor, sharpe_ratio
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run_id,
                fold["fold"],
                fold["train_bars"],
                fold["val_bars"],
                fold["trades"],
                fold["pnl"],
                fold["win_rate"],
                fold["profit_factor"],
                fold["sharpe_ratio"],
            ))

        conn.commit()
        conn.close()

        logger.info(f"Saved walk-forward results to {db_path} (run_id={run_id})")
        return run_id


def test_walkforward():
    """Test walk-forward analysis."""
    print("Testing Walk-Forward Analysis")
    print("=" * 70)

    # Load config
    config = Config.load('config/config.yaml.example')

    # Generate test data (60 days)
    print("Generating test data...")
    from bot.market_data import generate_realistic_bars
    bars = generate_realistic_bars(days=60, bars_per_day=78)
    print(f"Generated {len(bars)} bars\n")

    # Run walk-forward
    analyzer = WalkForwardAnalyzer(config)
    result = analyzer.run(
        bars=bars,
        n_folds=5,
        train_ratio=0.7,
        multiplier=5.0,
        slippage=0.25,
    )

    # Print report
    analyzer.print_report(result)

    # Save results
    run_id = analyzer.save_results(result)
    print(f"\n✅ Saved to database (run_id={run_id})")

    # Compare with simple backtest
    print("\n🔄 Comparison: Walk-Forward vs Simple Backtest")
    print("-" * 70)

    # Run simple backtest on same data
    from bot.backtest import BacktestEngine
    engine = BacktestEngine(config)
    simple_result = engine.run(bars=bars, multiplier=5.0, slippage=0.25)

    print(f"Walk-Forward: {len(result.folds)} folds | ${result.overall_pnl:,.2f} | {result.win_rate:.1f}%")
    print(f"Simple:       1 test     | ${simple_result.total_pnl:,.2f} | {simple_result.win_rate:.1f}%")

    diff = result.overall_pnl - simple_result.total_pnl
    print(f"\nDifference:    ${diff:,.2f} ({diff / abs(simple_result.total_pnl or 1) * 100:+.1f}%)")

    if diff < 0:
        print("⚠️  Walk-forward shows worse performance (expected - more realistic)")
    elif diff > 0:
        print("✅ Walk-forward shows better performance")

    print("\n✅ Walk-forward test complete!")


if __name__ == "__main__":
    test_walkforward()
