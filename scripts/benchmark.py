#!/usr/bin/env python3
"""
Performance Benchmark Tool

Measures performance of key bot components.
"""
import sys
sys.path.insert(0, '.')

import time
import statistics
import tracemalloc
from typing import Dict, List, Tuple
from bot.config import Config
from bot.backtest import BacktestEngine, generate_realistic_bars
from bot.core.signals import SignalGenerator


class Benchmark:
    """Benchmark runner"""

    def __init__(self):
        self.results = {}
        tracemalloc.start()

    def measure_signal_generation(
        self,
        iterations: int = 1000,
    ) -> Dict[str, float]:
        """Benchmark Z-Score signal generation."""
        print(f"  Measuring signal generation ({iterations} iterations)...")

        config = Config.load('config/config.yaml.example')
        signal_gen = SignalGenerator(config.strategy.lookback_period)

        # Warmup
        for _ in range(100):
            signal_gen.update(5000.0)

        # Measure
        times = []
        for _ in range(iterations):
            start = time.perf_counter()
            zscore = signal_gen.update(5000.0)
            end = time.perf_counter()
            times.append((end - start) * 1000)  # Convert to ms

        return {
            "mean_ms": statistics.mean(times),
            "median_ms": statistics.median(times),
            "min_ms": min(times),
            "max_ms": max(times),
            "std_ms": statistics.stdev(times) if len(times) > 1 else 0.0,
            "total_ms": sum(times),
        }

    def measure_backtest_engine(
        self,
        bars_count: int = 1000,
    ) -> Dict[str, float]:
        """Benchmark full backtest run."""
        print(f"  Measuring backtest engine ({bars_count} bars)...")

        config = Config.load('config/config.yaml.example')
        bars = generate_realistic_bars(days=15)

        engine = BacktestEngine(config)

        start = time.perf_counter()
        result = engine.run(bars=bars, multiplier=5.0, slippage=0.25)
        end = time.perf_counter()

        elapsed_ms = (end - start) * 1000

        # Get memory usage
        current, peak = tracemalloc.get_traced_memory()
        peak_mb = peak / 1024 / 1024

        return {
            "elapsed_ms": elapsed_ms,
            "bars_per_second": bars_count / (elapsed_ms / 1000),
            "trades": result.total_trades,
            "memory_peak_mb": peak_mb,
        }

    def measure_database_query(
        self,
        iterations: int = 100,
    ) -> Dict[str, float]:
        """Benchmark database operations."""
        print(f"  Measuring database queries ({iterations} iterations)...")

        import sqlite3
        from bot.backtest import BacktestEngine, Bar, BacktestResult
        from datetime import datetime

        # Create test DB
        conn = sqlite3.connect(":memory:")
        cursor = conn.cursor()

        # Create tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS test_bars (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                open REAL, high REAL, low REAL, close REAL, volume INTEGER
            )
        """)

        # Insert test data
        cursor.executemany("""
            INSERT INTO test_bars (timestamp, open, high, low, close, volume)
            VALUES (?, ?, ?, ?, ?, ?)
        """, [
            (datetime.utcnow().isoformat(), 5000.0, 5001.0, 4999.0, 5000.5, 100)
            for _ in range(1000)
        ])

        conn.commit()

        # Benchmark queries
        times = []
        for _ in range(iterations):
            start = time.perf_counter()
            cursor.execute("SELECT * FROM test_bars ORDER BY timestamp DESC LIMIT 100")
            cursor.fetchall()
            end = time.perf_counter()
            times.append((end - start) * 1000)

        conn.close()

        return {
            "mean_ms": statistics.mean(times),
            "median_ms": statistics.median(times),
            "p95_ms": sorted(times)[int(len(times) * 0.95)] if times else 0.0,
        }

    def measure_json_serialization(
        self,
        iterations: int = 1000,
    ) -> Dict[str, float]:
        """Benchmark JSON encoding/decoding."""
        print(f"  Measuring JSON operations ({iterations} iterations)...")

        import json
        from bot.backtest import Bar

        test_bar = Bar(
            timestamp=datetime.utcnow(),
            open=5000.0,
            high=5002.0,
            low=4998.0,
            close=5000.5,
            volume=100,
        )

        # Measure encoding
        encode_times = []
        for _ in range(iterations):
            start = time.perf_counter()
            json_str = json.dumps(test_bar.__dict__)
            end = time.perf_counter()
            encode_times.append((end - start) * 1000)

        # Measure decoding
        decode_times = []
        for _ in range(iterations):
            start = time.perf_counter()
            obj = json.loads(json_str)
            end = time.perf_counter()
            decode_times.append((end - start) * 1000)

        return {
            "encode_mean_ms": statistics.mean(encode_times),
            "decode_mean_ms": statistics.mean(decode_times),
            "json_size_bytes": len(json.dumps(test_bar.__dict__).encode()),
        }

    def run_full_benchmark(self) -> Dict[str, any]:
        """Run complete benchmark suite."""
        print("=" * 60)
        print("⚡ Performance Benchmark Suite")
        print("=" * 60)
        print()

        results = {}

        # 1. Signal Generation
        print("1. Signal Generation Benchmark")
        print("-" * 60)
        results['signal_gen'] = self.measure_signal_generation(iterations=1000)
        print()

        # 2. Backtest Engine
        print("2. Backtest Engine Benchmark")
        print("-" * 60)
        results['backtest'] = self.measure_backtest_engine(bars_count=2340)
        print()

        # 3. Database Queries
        print("3. Database Query Benchmark")
        print("-" * 60)
        results['database'] = self.measure_database_query(iterations=100)
        print()

        # 4. JSON Operations
        print("4. JSON Operations Benchmark")
        print("-" * 60)
        results['json'] = self.measure_json_serialization(iterations=1000)
        print()

        # Print summary
        self.print_summary(results)

        return results

    def print_summary(self, results: Dict):
        """Print benchmark summary."""
        print("=" * 60)
        print("📊 BENCHMARK SUMMARY")
        print("=" * 60)
        print()

        # Signal Generation
        sg = results['signal_gen']
        print("1. Signal Generation (1000 calls)")
        print(f"   Mean:    {sg['mean_ms']:.3f} ms")
        print(f"   Median:  {sg['median_ms']:.3f} ms")
        print(f"   Min:     {sg['min_ms']:.3f} ms")
        print(f"   Max:     {sg['max_ms']:.3f} ms")
        print(f"   Std Dev: {sg['std_ms']:.3f} ms")
        print(f"   Total:   {sg['total_ms']:.1f} ms")
        print()

        # Backtest Engine
        bt = results['backtest']
        print("2. Backtest Engine (2340 bars)")
        print(f"   Time:      {bt['elapsed_ms']:.1f} ms ({bt['elapsed_ms']/1000:.2f}s)")
        print(f"   Speed:     {bt['bars_per_second']:.0f} bars/sec")
        print(f"   Trades:    {bt['trades']}")
        print(f"   Memory:    {bt['memory_peak_mb']:.2f} MB (peak)")
        print()

        # Database Queries
        db = results['database']
        print("3. Database Queries (100 iterations)")
        print(f"   Mean:     {db['mean_ms']:.3f} ms")
        print(f"   Median:   {db['median_ms']:.3f} ms")
        print(f"   P95:      {db['p95_ms']:.3f} ms")
        print()

        # JSON Operations
        json_res = results['json']
        print("4. JSON Operations (1000 iterations)")
        print(f"   Encode:   {json_res['encode_mean_ms']:.3f} ms")
        print(f"   Decode:   {json_res['decode_mean_ms']:.3f} ms")
        print(f"   Size:     {json_res['json_size_bytes']} bytes")
        print()

        # Performance grades
        self.print_performance_grades(results)

        print()
        print("=" * 60)
        print("✅ Benchmark Complete!")
        print("=" * 60)

    def print_performance_grades(self, results: Dict):
        """Print performance grades."""
        print("📈 Performance Grades")
        print("-" * 60)

        # Signal generation
        sg_mean = results['signal_gen']['mean_ms']
        if sg_mean < 0.01:
            sg_grade = "🟢 Excellent"
        elif sg_mean < 0.05:
            sg_grade = "🟡 Good"
        elif sg_mean < 0.1:
            sg_grade = "🟠 OK"
        else:
            sg_grade = "🔴 Needs Improvement"

        print(f"   Signal Generation:  {sg_grade} ({sg_mean*1000:.2f} µs)")

        # Backtest speed
        bt_speed = results['backtest']['bars_per_second']
        if bt_speed > 10000:
            bt_grade = "🟢 Excellent"
        elif bt_speed > 5000:
            bt_grade = "🟡 Good"
        elif bt_speed > 2000:
            bt_grade = "🟠 OK"
        else:
            bt_grade = "🔴 Needs Improvement"

        print(f"   Backtest Speed:      {bt_grade} ({bt_speed:.0f} bars/sec)")

        # Database
        db_mean = results['database']['mean_ms']
        if db_mean < 1.0:
            db_grade = "🟢 Excellent"
        elif db_mean < 5.0:
            db_grade = "🟡 Good"
        elif db_mean < 10.0:
            db_grade = "🟠 OK"
        else:
            db_grade = "🔴 Needs Improvement"

        print(f"   Database Queries:   {db_grade} ({db_mean:.2f} ms)")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Performance benchmark tool")
    parser.add_argument("--iterations", type=int, default=1000,
                       help="Number of iterations for micro-benchmarks")
    parser.add_argument("--quick", action="store_true",
                       help="Run quick benchmark (fewer iterations)")

    args = parser.parse_args()

    iterations = 100 if args.quick else args.iterations

    benchmark = Benchmark()

    if args.quick:
        # Quick benchmark
        print(f"Running quick benchmark ({iterations} iterations)...")
        results = benchmark.run_full_benchmark()
    else:
        # Full benchmark
        print(f"Running full benchmark ({iterations} iterations)...")
        results = benchmark.run_full_benchmark()


if __name__ == "__main__":
    main()
