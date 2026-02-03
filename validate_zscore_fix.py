"""
Validation script for Z-Score numerical stability fix
Demonstrates the fix for catastrophic cancellation issue
"""

import sys
sys.path.insert(0, './python')
sys.path.insert(0, './rust/target/debug')

import numpy as np

# Try to import the Rust version
try:
    import quant_scalper_rust as qsr
    RUST_AVAILABLE = True
except ImportError:
    print("⚠️  Rust module not found. Building...")
    import subprocess
    subprocess.run(['maturin', 'develop', '--release'], cwd='rust', check=True)
    import quant_scalper_rust as qsr
    RUST_AVAILABLE = True

print("=" * 70)
print("Z-SCORE NUMERICAL STABILITY VALIDATION")
print("=" * 70)

def test_small_values():
    """Test with small values - both algorithms should work"""
    print("\n📊 Test 1: Small values (should be accurate for both)")
    print("-" * 50)

    prices = [100.0 + i * 0.1 for i in range(20)]
    lookback = 10

    # NumPy reference
    window = prices[-lookback:]
    mean_np = np.mean(window)
    std_np = np.std(window, ddof=1)  # ddof=1 for sample std
    z_np = (window[-1] - mean_np) / std_np

    # Rust shifted data algorithm
    engine = qsr.ZScoreEngine(lookback)
    for price in prices:
        z_rust = engine.update(price)

    print(f"NumPy Z-Score:     {z_np:.6f}")
    print(f"Rust Z-Score:      {z_rust:.6f}")
    print(f"Difference:        {abs(z_np - z_rust):.6f}")
    print(f"Status:            ✅ PASS" if abs(z_np - z_rust) < 0.1 else "❌ FAIL")

    return abs(z_np - z_rust) < 0.1


def test_wikipedia_example():
    """
    Test Wikipedia's catastrophic cancellation example
    With naive algorithm: variance = -170.666 (WRONG!)
    With fixed algorithm: variance = 30 (CORRECT)
    """
    print("\n📊 Test 2: Wikipedia Catastrophic Cancellation Example")
    print("-" * 50)

    offset = 1_000_000_000.0  # 1 billion
    prices = [offset + 4.0, offset + 7.0, offset + 13.0, offset + 16.0]
    lookback = 4

    # Naive calculation (demonstrates the bug)
    n = len(prices)
    mean_naive = sum(prices) / n
    sum_sq = sum(p * p for p in prices)
    variance_naive = (sum_sq / n) - (mean_naive * mean_naive)

    # NumPy (correct)
    std_np = np.std(prices, ddof=1)
    variance_np = std_np ** 2

    # Rust shifted data algorithm
    engine = qsr.ZScoreEngine(lookback)
    for price in prices:
        z_rust = engine.update(price)

    std_rust = engine.get_std()
    variance_rust = std_rust ** 2

    print(f"Price offset:       {offset:,.0f}")
    print(f"Expected variance:  30.0")
    print(f"Naive variance:     {variance_naive:.6f} ❌")
    print(f"NumPy variance:    {variance_np:.6f} ✅")
    print(f"Rust variance:     {variance_rust:.6f} ✅")
    print(f"Status:            ✅ PASS" if abs(variance_rust - 30.0) < 0.1 else "❌ FAIL")

    return abs(variance_rust - 30.0) < 0.1


def test_large_values():
    """Test with very large values that would break naive algorithm"""
    print("\n📊 Test 3: Very large values (1e15 scale)")
    print("-" * 50)

    huge_offset = 1e15
    prices = [huge_offset + (i % 3) for i in range(30)]
    lookback = 20

    # NumPy
    window = prices[-lookback:]
    std_np = np.std(window, ddof=1)

    # Rust
    engine = qsr.ZScoreEngine(lookback)
    for price in prices:
        z_rust = engine.update(price)

    std_rust = engine.get_std()

    print(f"Price scale:        {huge_offset:.0e}")
    print(f"NumPy std:          {std_np:.6f}")
    print(f"Rust std:           {std_rust:.6f}")
    print(f"Difference:         {abs(std_np - std_rust):.6f}")
    print(f"Finite check:       {'✅' if std_rust.is_finite() else '❌'}")
    print(f"Positive check:     {'✅' if std_rust > 0 else '❌'}")

    return std_rust.is_finite() and std_rust > 0


def test_realistic_btc_prices():
    """Test with realistic BTC price data"""
    print("\n📊 Test 4: Realistic BTC prices (~$50,000)")
    print("-" * 50)

    base_price = 50_000.0
    np.random.seed(42)
    # Simulate realistic price movement
    prices = []
    for i in range(100):
        price = base_price + np.sin(i * 0.1) * 500 + np.random.randn() * 100
        prices.append(price)

    lookback = 20

    # NumPy
    window = prices[-lookback:]
    mean_np = np.mean(window)
    std_np = np.std(window, ddof=1)
    z_np = (window[-1] - mean_np) / std_np

    # Rust
    engine = qsr.ZScoreEngine(lookback)
    for price in prices:
        z_rust = engine.update(price)

    mean_rust = engine.get_mean()
    std_rust = engine.get_std()

    print(f"Current price:      ${prices[-1]:,.2f}")
    print(f"Mean (NumPy):       ${mean_np:,.2f}")
    print(f"Mean (Rust):        ${mean_rust:,.2f}")
    print(f"Std (NumPy):        ${std_np:.2f}")
    print(f"Std (Rust):         ${std_rust:.2f}")
    print(f"Z-Score (NumPy):    {z_np:.6f}")
    print(f"Z-Score (Rust):     {z_rust:.6f}")
    print(f"Z-Score difference: {abs(z_np - z_rust):.6f}")

    # Should be very close for realistic prices
    return abs(z_np - z_rust) < 0.01


def test_zero_variance():
    """Test edge case: zero variance"""
    print("\n📊 Test 5: Zero variance (all same price)")
    print("-" * 50)

    prices = [100.0] * 20
    lookback = 10

    engine = qsr.ZScoreEngine(lookback)
    for price in prices:
        z = engine.update(price)

    std = engine.get_std()

    print(f"All prices:         100.0")
    print(f"Std dev:            {std:.6f}")
    print(f"Z-Score:            {z:.6f}")
    print(f"Status:            ✅ PASS" if abs(z) < 1e-10 and std >= 0 else "❌ FAIL")

    return abs(z) < 1e-10 and std >= 0


def test_sliding_window_accuracy():
    """Test that sliding window maintains accuracy over time"""
    print("\n📊 Test 6: Long sequence stability (1000 updates)")
    print("-" * 50)

    np.random.seed(123)
    base = 1_000_000.0
    prices = [base + np.sin(i * 0.01) * 1000 for i in range(1000)]
    lookback = 50

    engine = qsr.ZScoreEngine(lookback)

    # Track drift over time
    max_diff = 0
    for i, price in enumerate(prices):
        z_rust = engine.update(price)

        if i >= lookback:
            # Compare with NumPy calculation
            window = prices[i-lookback+1:i+1]
            z_np = (window[-1] - np.mean(window)) / np.std(window, ddof=1)
            diff = abs(z_rust - z_np)
            max_diff = max(max_diff, diff)

    print(f"Total updates:      1000")
    print(f"Lookback:           50")
    print(f"Max Z-Score diff:   {max_diff:.6f}")
    print(f"Status:            ✅ PASS" if max_diff < 0.1 else "❌ FAIL")

    return max_diff < 0.1


if __name__ == "__main__":
    print("\nRunning validation tests...\n")

    results = []
    results.append(("Small values", test_small_values()))
    results.append(("Wikipedia example", test_wikipedia_example()))
    results.append(("Large values (1e15)", test_large_values()))
    results.append(("Realistic BTC prices", test_realistic_btc_prices()))
    results.append(("Zero variance", test_zero_variance()))
    results.append(("Long sequence", test_sliding_window_accuracy()))

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{name:.<50} {status}")

    total = len(results)
    passed = sum(1 for _, p in results if p)

    print("=" * 70)
    print(f"Result: {passed}/{total} tests passed")
    print("=" * 70)

    if passed == total:
        print("\n🎉 All validation tests passed! The Z-Score fix is working correctly.")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. Please review the implementation.")
        sys.exit(1)
