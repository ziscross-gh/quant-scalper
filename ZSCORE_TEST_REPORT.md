# Z-Score Numerical Stability Test Report
**Test Engineer:** Sofia (QA)
**Date:** 2026-02-03
**Component:** `rust/src/zscore.rs`

## Executive Summary

The Z-Score implementation has **CRITICAL numerical stability issues** that will cause incorrect calculations with large values. The current approach uses a naive sum-based variance calculation that suffers from catastrophic cancellation.

## Test Results

### ✅ Passed Tests (24/26)
- Basic functionality tests
- Small values accuracy
- Zero variance handling
- Sliding window operations
- Batch updates
- Nearly zero variance
- Very large values (1e15)
- Mixed scale values
- Negative large values
- Consistency across lookbacks
- Long sequence stability
- Extreme value recovery

### ❌ Failed Tests (2/26)

#### 1. **test_large_values_stability** - CRITICAL
```
Large values: Std dev drifted too much.
Got: 11.313708498984761
Expected: ~0.816
```

**Analysis:**
- Values: 1,000,000,000 to 1,000,000,002 (small variation around large offset)
- Expected std dev: ~0.816 (std dev of [0, 1, 2])
- Actual std dev: 11.31 (1300% error!)
- Root cause: Catastrophic cancellation in variance calculation

#### 2. **test_variance_never_negative** - CRITICAL
```
Variance significantly negative: -16384
```

**Analysis:**
- The naive variance formula `(sum_sq / n) - (mean * mean)` produces negative values
- Negative variance is mathematically impossible
- Caused by floating-point precision loss when subtracting large, nearly equal numbers
- The code checks `variance < 0.0` but it's already too late - precision is lost

## Root Cause Analysis

### Current Implementation (Problematic)
```rust
let variance = (self.sum_sq / n) - (mean * mean);
```

This is the **naive two-pass algorithm**:
- `sum_sq` = Σx² (can overflow/lose precision)
- `mean²` = (Σx/n)² (also large)
- Subtracting two large, nearly equal numbers = catastrophic cancellation

**Example of the problem:**
```
For values around 1e10 with small variations:
sum_sq ≈ 1e20
mean² ≈ 1e20
Variance = sum_sq/n - mean² = 1e20 - 1e20 = ??? (precision lost)
```

### Solution: Welford's Algorithm

Welford's online algorithm maintains:
- `mean`: Running average
- `M2`: Sum of squared differences from the current mean

**Update formula:**
```
δ = x - mean
mean = mean + δ / n
M2 = M2 + δ * (x - mean)  # or δ * (x - new_mean)
```

**Variance:**
```
variance = M2 / n
```

**Why Welford's is better:**
- Only one pass needed
- No subtraction of large numbers
- Numerically stable even for extreme values
- Perfect for streaming/rolling windows

## Implementation Recommendations

### Option 1: True Welford's Algorithm (RECOMMENDED)
Replace the sum-based approach with Welford's online algorithm:

```rust
pub struct ZScoreEngine {
    prices: VecDeque<f64>,
    lookback: usize,
    count: f64,       // n
    mean: f64,        // Current mean
    m2: f64,          // Sum of squared differences
}
```

### Option 2: Kahan Summation (Better than current)
If Welford's is too complex to implement quickly, at least use Kahan summation for `sum` and `sum_sq`:

```rust
// Kahan compensated summation
let y = value - compensation;
let t = sum + y;
compensation = (t - sum) - y;
sum = t;
```

### Option 3: Shift to Zero Range
Before calculating, subtract the mean from all values:

```rust
// This reduces magnitude before calculation
let shifted: Vec<f64> = prices.iter().map(|&x| x - mean).collect();
// Then calculate on shifted values
```

## Impact Assessment

### High Risk Scenarios
- ✅ **Trading prices in USD:** 1,000 - 100,000 (SAFE - values are reasonable)
- ✅ **Crypto prices in satoshis:** 10,000,000,000+ (SAFE for most coins)
- ⚠️ **Large market caps:** 1,000,000,000,000+ (RISK - precision loss)
- ❌ **Scientific data:** Values 1e15+ (CRITICAL - will fail)

### Current Production Impact
If you're trading:
- **Forex pairs (USD/JPY, EUR/USD):** Safe (1-200 range)
- **Stocks (AAPL, GOOGL):** Safe (100-3000 range)
- **Crypto in USD:** Safe (0.01 - 100,000 range)
- **Crypto in satoshis:** RISK (1e10+ range)

**Verdict:** For typical trading prices, the current implementation **may work** but will have reduced precision. For high-precision requirements or large value ranges, it will fail.

## Testing Recommendations

1. **Immediate:** Fix the variance calculation
2. **Add:** Property-based testing with QuickCheck
3. **Add:** Fuzz testing for edge cases
4. **Monitor:** Track Z-score drift in production
5. **Validate:** Compare with Python's numpy implementation for reference

## Next Steps for Kai (Developer)

1. **Priority 1:** Implement Welford's algorithm
2. **Priority 2:** Re-run all stability tests
3. **Priority 3:** Add benchmarks (ensure no performance regression)
4. **Priority 4:** Add integration tests with Python bindings

## Conclusion

The current Z-Score implementation has **critical numerical stability issues** that MUST be fixed before production use with large values. The naive sum-based variance calculation is fundamentally flawed and will produce incorrect results.

**Status:** ❌ DO NOT DEPLOY in current state
**Recommendation:** Implement Welford's algorithm immediately

---

**Reported by:** Sofia, QA Engineer
**Reviewed by:** [Pending - Arun/Marcus]
**Assigned to:** Kai (Developer)
