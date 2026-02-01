"""
Backtest Engine

Simulates trading strategy on historical data to test performance.
"""
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path

from ..config import Config
from ..core.signals import SignalGenerator
from ..utils.helpers import calculate_pnl

logger = logging.getLogger(__name__)


@dataclass
class BacktestPosition:
    """Position state during backtest"""
    entry_price: float = 0.0
    entry_time: datetime = None
    quantity: int = 0
    entry_zscore: float = 0.0


@dataclass
class BacktestResult:
    """Backtest performance metrics"""
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    total_pnl: float = 0.0
    max_drawdown: float = 0.0
    max_profit: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    profit_factor: float = 0.0
    sharpe_ratio: float = 0.0
    trades: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class Bar:
    """OHLCV bar"""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


class BacktestEngine:
    """Backtest engine for strategy testing"""

    def __init__(self, config: Config):
        self.config = config
        self.signal_gen = SignalGenerator(config.strategy.lookback_period)
        self.position: Optional[BacktestPosition] = None

    def run(
        self,
        bars: List[Bar],
        multiplier: float = 5.0,  # MES contract multiplier
        slippage: float = 0.25,  # 1 tick
    ) -> BacktestResult:
        """
        Run backtest on historical bars.

        Args:
            bars: List of OHLCV bars (must be time-sorted)
            multiplier: Contract value multiplier
            slippage: Price slippage per trade (in ticks)

        Returns:
            BacktestResult with performance metrics
        """
        logger.info(f"Running backtest on {len(bars)} bars...")

        result = BacktestResult()
        peak_equity = 0.0
        equity_curve = [0.0]
        current_equity = 0.0

        for bar in bars:
            # Update signal generator
            zscore = self.signal_gen.update(bar.close)

            if not self.signal_gen.is_ready():
                continue

            # Generate signal
            signal = self.signal_gen.get_signal(
                z_threshold_entry=self.config.strategy.z_threshold_entry,
                z_threshold_exit=self.config.strategy.z_threshold_exit,
            )

            if not signal:
                continue

            signal_type = signal["type"]

            # Handle signals
            if signal_type == "ENTER_LONG" and self.position is None:
                # Enter long
                self.position = BacktestPosition(
                    entry_price=bar.close + slippage,
                    entry_time=bar.timestamp,
                    quantity=1,
                    entry_zscore=zscore,
                )

            elif signal_type == "ENTER_SHORT" and self.position is None:
                # Enter short
                self.position = BacktestPosition(
                    entry_price=bar.close + slippage,
                    entry_time=bar.timestamp,
                    quantity=-1,
                    entry_zscore=zscore,
                )

            elif signal_type == "EXIT" and self.position is not None:
                # Exit position
                exit_price = bar.close + slippage
                pnl = calculate_pnl(
                    entry_price=self.position.entry_price,
                    exit_price=exit_price,
                    quantity=self.position.quantity,
                    multiplier=multiplier,
                )

                # Record trade
                trade = {
                    "timestamp": bar.timestamp,
                    "entry_price": self.position.entry_price,
                    "exit_price": exit_price,
                    "quantity": self.position.quantity,
                    "pnl": pnl,
                    "entry_zscore": self.position.entry_zscore,
                    "exit_zscore": zscore,
                    "duration": bar.timestamp - self.position.entry_time,
                }
                result.trades.append(trade)

                # Update stats
                result.total_trades += 1
                current_equity += pnl
                equity_curve.append(current_equity)

                if pnl >= 0:
                    result.winning_trades += 1
                else:
                    result.losing_trades += 1

                # Track drawdown
                if current_equity > peak_equity:
                    peak_equity = current_equity

                drawdown = peak_equity - current_equity
                if drawdown > result.max_drawdown:
                    result.max_drawdown = drawdown

                # Track profit
                if current_equity > result.max_profit:
                    result.max_profit = current_equity

                # Reset position
                self.position = None

        # Calculate final metrics
        result.total_pnl = current_equity
        result.win_rate = (
            result.winning_trades / result.total_trades * 100
            if result.total_trades > 0 else 0.0
        )

        # Average win/loss
        wins = [t["pnl"] for t in result.trades if t["pnl"] > 0]
        losses = [t["pnl"] for t in result.trades if t["pnl"] < 0]

        result.avg_win = sum(wins) / len(wins) if wins else 0.0
        result.avg_loss = sum(losses) / len(losses) if losses else 0.0

        # Profit factor
        total_wins = sum(wins)
        total_losses = abs(sum(losses))
        result.profit_factor = (
            total_wins / total_losses if total_losses > 0 else 0.0
        )

        # Sharpe ratio (simplified)
        if len(equity_curve) > 1:
            import statistics
            returns = [
                (equity_curve[i] - equity_curve[i-1])
                for i in range(1, len(equity_curve))
            ]
            if returns:
                avg_return = statistics.mean(returns)
                std_return = statistics.stdev(returns) if len(returns) > 1 else 0.0001
                result.sharpe_ratio = (
                    (avg_return / std_return) * (252 ** 0.5)
                    if std_return > 0 else 0.0
                )

        logger.info(f"Backtest complete: {result.total_trades} trades, ${result.total_pnl:.2f} P&L")
        return result

    def save_trades_to_db(self, result: BacktestResult, db_path: str = "data/backtest_trades.db"):
        """
        Save backtest trades to SQLite database.

        Args:
            result: BacktestResult from run()
            db_path: Database file path
        """
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Create table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS backtest_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                total_trades INTEGER,
                total_pnl REAL,
                win_rate REAL,
                max_drawdown REAL,
                profit_factor REAL,
                sharpe_ratio REAL,
                parameters TEXT
            )
        """)

        # Create trades table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS backtest_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER,
                timestamp TEXT NOT NULL,
                entry_price REAL,
                exit_price REAL,
                quantity INTEGER,
                pnl REAL,
                entry_zscore REAL,
                exit_zscore REAL,
                duration_minutes REAL,
                FOREIGN KEY (run_id) REFERENCES backtest_runs (id)
            )
        """)

        # Insert run
        params = {
            "lookback": self.config.strategy.lookback_period,
            "z_entry": self.config.strategy.z_threshold_entry,
            "z_exit": self.config.strategy.z_threshold_exit,
        }
        cursor.execute("""
            INSERT INTO backtest_runs (
                timestamp, total_trades, total_pnl, win_rate,
                max_drawdown, profit_factor, sharpe_ratio, parameters
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.utcnow().isoformat(),
            result.total_trades,
            result.total_pnl,
            result.win_rate,
            result.max_drawdown,
            result.profit_factor,
            result.sharpe_ratio,
            str(params),
        ))

        run_id = cursor.lastrowid

        # Insert trades
        for trade in result.trades:
            cursor.execute("""
                INSERT INTO backtest_trades (
                    run_id, timestamp, entry_price, exit_price,
                    quantity, pnl, entry_zscore, exit_zscore, duration_minutes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run_id,
                trade["timestamp"].isoformat(),
                trade["entry_price"],
                trade["exit_price"],
                trade["quantity"],
                trade["pnl"],
                trade["entry_zscore"],
                trade["exit_zscore"],
                trade["duration"].total_seconds() / 60,
            ))

        conn.commit()
        conn.close()

        logger.info(f"Saved backtest to {db_path} (run_id={run_id})")
        return run_id


def generate_test_bars(days: int = 30, bars_per_day: int = 78) -> List[Bar]:
    """
    Generate synthetic bars for testing backtest engine.

    Simulates a mean-reverting price series with some trend and noise.

    Args:
        days: Number of days of data
        bars_per_day: Bars per day (5-minute bars = 78)

    Returns:
        List of Bar objects
    """
    import random

    bars = []
    current_time = datetime.utcnow() - timedelta(days=days)

    # Simulated price with mean reversion
    price = 5000.0
    mean = 5000.0

    for i in range(days * bars_per_day):
        # Random walk with mean reversion
        noise = random.gauss(0, 0.5)
        reversion = (mean - price) * 0.05

        price = price + noise + reversion

        # Add OHLC structure
        high = price + abs(random.gauss(0, 0.2))
        low = price - abs(random.gauss(0, 0.2))
        close = price
        open_price = price - (random.gauss(0, 0.3))

        volume = random.randint(100, 500)

        bar = Bar(
            timestamp=current_time,
            open=open_price,
            high=high,
            low=low,
            close=close,
            volume=volume,
        )

        bars.append(bar)

        # Advance time (5-minute bars)
        current_time += timedelta(minutes=5)

    return bars


def print_backtest_report(result: BacktestResult):
    """Print formatted backtest report"""
    print("=" * 60)
    print("BACKTEST REPORT")
    print("=" * 60)
    print()
    print("📊 Performance Metrics")
    print("-" * 60)
    print(f"  Total Trades:        {result.total_trades}")
    print(f"  Winning Trades:      {result.winning_trades}")
    print(f"  Losing Trades:       {result.losing_trades}")
    print(f"  Win Rate:           {result.win_rate:.2f}%")
    print()
    print("💰 Financial Results")
    print("-" * 60)
    print(f"  Total P&L:          ${result.total_pnl:,.2f}")
    print(f"  Max Profit:          ${result.max_profit:,.2f}")
    print(f"  Max Drawdown:        ${result.max_drawdown:,.2f}")
    print(f"  Avg Win:             ${result.avg_win:,.2f}")
    print(f"  Avg Loss:            ${result.avg_loss:,.2f}")
    print(f"  Profit Factor:        {result.profit_factor:.2f}")
    print()
    print("📈 Risk Metrics")
    print("-" * 60)
    print(f"  Sharpe Ratio:        {result.sharpe_ratio:.2f}")
    print(f"  Profit per Trade:     ${result.total_pnl / result.total_trades if result.total_trades else 0:.2f}")
    print()

    if result.trades:
        print("📋 Last 10 Trades")
        print("-" * 60)
        for trade in result.trades[-10:]:
            direction = "LONG" if trade["quantity"] > 0 else "SHORT"
            pnl_color = "🟢" if trade["pnl"] >= 0 else "🔴"
            print(f"  {trade['timestamp'].strftime('%Y-%m-%d %H:%M')} | "
                  f"{direction:5s} | "
                  f"{pnl_color} ${trade['pnl']:6.2f} | "
                  f"Z: {trade['entry_zscore']:5.2f} → {trade['exit_zscore']:5.2f}")

    print()
    print("=" * 60)


def test_backtest():
    """Test backtest engine with synthetic data"""
    print("Testing Backtest Engine...")
    print("=" * 60)

    # Load config
    config = Config.load('config/config.yaml.example')

    # Generate synthetic data
    print("Generating synthetic data (30 days)...")
    bars = generate_test_bars(days=30, bars_per_day=78)
    print(f"Generated {len(bars)} bars\n")

    # Run backtest
    engine = BacktestEngine(config)
    result = engine.run(bars=bars, multiplier=5.0, slippage=0.25)

    # Print report
    print_backtest_report(result)

    # Save to database
    run_id = engine.save_trades_to_db(result)
    print(f"\n✅ Backtest saved to database (run_id={run_id})")

    # Test loading from database
    print("\n📁 Loading from database...")
    conn = sqlite3.connect("data/backtest_trades.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, timestamp, total_trades, total_pnl, win_rate
        FROM backtest_runs
        ORDER BY id DESC
        LIMIT 5
    """)

    print("Recent backtest runs:")
    for row in cursor.fetchall():
        print(f"  Run #{row[0]} | {row[1][:16]} | "
              f"{row[2]} trades | ${row[3]:.2f} | {row[4]:.1f}%")

    conn.close()

    print("\n✅ Backtest test complete!")


if __name__ == "__main__":
    test_backtest()
