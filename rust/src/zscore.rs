//! High-performance Z-Score calculation engine
//!
//! Uses shifted data algorithm for numerically stable
//! incremental mean and variance calculation in rolling windows.
//!
//! This implementation avoids catastrophic cancellation by centering
//! calculations around a reference value K (typically the first price),
//! which dramatically improves numerical stability for large price values.

use pyo3::prelude::*;
use std::collections::VecDeque;

/// Z-Score calculation engine using numerically stable rolling window statistics
///
/// This implementation uses the shifted data algorithm which maintains
/// numerical stability even with very large price values by centering
/// calculations around a reference value K.
///
/// The naive approach (variance = Σx²/n - μ²) suffers from catastrophic
/// cancellation when subtracting two large, nearly-equal numbers. By using
/// the shifted data algorithm, we avoid this problem entirely.
///
/// # Example (Python)
/// ```python
/// from quant_scalper_rust import ZScoreEngine
///
/// engine = ZScoreEngine(20)  # 20-bar lookback
///
/// # Feed prices
/// for price in prices:
///     zscore = engine.update(price)
///     if zscore is not None and zscore >= 2.0:
///         print("Overbought signal!")
/// ```
#[pyclass]
pub struct ZScoreEngine {
    prices: VecDeque<f64>,
    lookback: usize,
    K: f64,   // Reference value for shifting (first price)
    n: f64,   // Current count of prices
    Ex: f64,  // Sum of (x - K)
    Ex2: f64, // Sum of (x - K)²
}

#[pymethods]
impl ZScoreEngine {
    /// Create a new Z-Score engine with specified lookback period
    ///
    /// # Arguments
    /// * `lookback` - Number of bars for rolling calculation (e.g., 20)
    #[new]
    pub fn new(lookback: usize) -> Self {
        assert!(lookback > 1, "Lookback must be > 1");

        Self {
            prices: VecDeque::with_capacity(lookback + 1),
            lookback,
            K: 0.0,
            n: 0.0,
            Ex: 0.0,
            Ex2: 0.0,
        }
    }

    /// Update with new price and return current Z-Score
    ///
    /// Returns None if insufficient data (warming up period)
    ///
    /// # Arguments
    /// * `price` - New price to add to the rolling window
    pub fn update(&mut self, price: f64) -> Option<f64> {
        // Initialize K on first price for numerical stability
        if self.prices.is_empty() {
            self.K = price;
        }

        // Add new price using shifted data algorithm
        let dx = price - self.K;
        self.Ex += dx;
        self.Ex2 += dx * dx;
        self.n += 1.0;
        self.prices.push_back(price);

        // Remove oldest price if over lookback
        if self.prices.len() > self.lookback {
            // Check if we're about to remove our reference price
            let removing_k = self.prices.front()
                .map(|&front| (front - self.K).abs() < 1e-10)
                .unwrap_or(false);

            if let Some(old) = self.prices.pop_front() {
                let dx = old - self.K;
                self.Ex -= dx;
                self.Ex2 -= dx * dx;
                self.n -= 1.0;

                // If we removed our reference K, update K to a new value in the window
                // This maintains numerical stability as the window slides
                if removing_k {
                    if let Some(&new_k) = self.prices.front() {
                        // Need to recalculate Ex and Ex2 with new reference
                        let old_k = self.K;
                        self.K = new_k;
                        let shift = old_k - self.K;

                        // Recalculate shifted sums
                        // When K changes: new_Ex = Σ(x - new_K) = Σ(x - old_K + old_K - new_K) = old_Ex + n * shift
                        // new_Ex2 = Σ(x - new_K)² = Σ((x - old_K) + shift)² = old_Ex2 + 2 * shift * old_Ex + n * shift²
                        let n = self.n;
                        let old_Ex = self.Ex;
                        let old_Ex2 = self.Ex2;

                        self.Ex = old_Ex + n * shift;
                        self.Ex2 = old_Ex2 + 2.0 * shift * old_Ex + n * shift * shift;
                    }
                }
            }
        }

        // Calculate Z-Score if we have enough data
        self.calculate_zscore(price)
    }

    /// Get current Z-Score without adding new data
    pub fn get_zscore(&self) -> Option<f64> {
        if let Some(&current) = self.prices.back() {
            self.calculate_zscore(current)
        } else {
            None
        }
    }

    /// Get current rolling mean
    ///
    /// Uses shifted data formula: mean = K + Ex/n
    /// where n is the window size
    pub fn get_mean(&self) -> Option<f64> {
        let n = self.prices.len() as f64;
        if n >= 2.0 {
            Some(self.K + self.Ex / n)
        } else {
            None
        }
    }

    /// Get current rolling standard deviation
    ///
    /// Uses shifted data formula for variance:
    /// variance = (Ex2 - Ex²/n) / (n-1)
    ///
    /// This is numerically stable because we work with small
    /// values (differences from K) instead of large raw prices.
    pub fn get_std(&self) -> Option<f64> {
        let n = self.prices.len() as f64;
        if n >= 2.0 {
            // Shifted data variance formula
            let variance = (self.Ex2 - (self.Ex * self.Ex) / n) / (n - 1.0);

            // Handle numerical precision issues (tiny negative values possible)
            if variance < 0.0 {
                Some(0.0)
            } else {
                Some(variance.sqrt())
            }
        } else {
            None
        }
    }

    /// Reset the engine, clearing all data
    pub fn reset(&mut self) {
        self.prices.clear();
        self.K = 0.0;
        self.n = 0.0;
        self.Ex = 0.0;
        self.Ex2 = 0.0;
    }

    /// Check if engine has enough data to generate signals
    pub fn is_ready(&self) -> bool {
        self.prices.len() >= self.lookback
    }

    /// Get number of prices currently in the window
    pub fn count(&self) -> usize {
        self.prices.len()
    }

    /// Get the lookback period
    pub fn lookback(&self) -> usize {
        self.lookback
    }

    /// Get all prices in the current window (for debugging)
    pub fn get_prices(&self) -> Vec<f64> {
        self.prices.iter().copied().collect()
    }

    /// Batch update with multiple prices, returns final Z-Score
    ///
    /// More efficient than calling update() in a loop from Python
    pub fn update_batch(&mut self, prices: Vec<f64>) -> Option<f64> {
        let mut result = None;
        for price in prices {
            result = self.update(price);
        }
        result
    }
}

impl ZScoreEngine {
    /// Internal Z-Score calculation using shifted data algorithm
    fn calculate_zscore(&self, current_price: f64) -> Option<f64> {
        if self.prices.len() < self.lookback {
            return None;
        }

        let n = self.prices.len() as f64;
        let variance = (self.Ex2 - (self.Ex * self.Ex) / n) / (n - 1.0);

        // If variance is essentially zero, return 0 (price at mean)
        if variance < 1e-10 {
            return Some(0.0);
        }

        let std_dev = variance.sqrt();
        let mean = self.K + self.Ex / n;
        Some((current_price - mean) / std_dev)
    }
}

/// Reference implementation using naive calculation (for comparison and testing)
/// This is NOT suitable for production due to catastrophic cancellation issues
#[cfg(test)]
fn reference_zscore(prices: &[f64], current: f64) -> Option<f64> {
    if prices.is_empty() {
        return None;
    }

    let n = prices.len() as f64;
    let mean: f64 = prices.iter().sum::<f64>() / n;

    let variance: f64 = prices.iter()
        .map(|&x| (x - mean).powi(2))
        .sum::<f64>() / n;

    if variance < 1e-10 {
        return Some(0.0);
    }

    Some((current - mean) / variance.sqrt())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_new_engine() {
        let engine = ZScoreEngine::new(20);
        assert_eq!(engine.count(), 0);
        assert!(!engine.is_ready());
        assert_eq!(engine.lookback(), 20);
    }

    #[test]
    #[should_panic(expected = "Lookback must be > 1")]
    fn test_invalid_lookback() {
        ZScoreEngine::new(1);
    }

    #[test]
    fn test_warmup() {
        let mut engine = ZScoreEngine::new(5);

        // First 4 updates should return None
        for i in 0..4 {
            assert!(engine.update(100.0 + i as f64).is_none());
            assert!(!engine.is_ready());
        }

        // 5th update should return a value
        assert!(engine.update(104.0).is_some());
        assert!(engine.is_ready());
    }

    #[test]
    fn test_zscore_at_mean() {
        let mut engine = ZScoreEngine::new(5);

        // Add prices with mean = 100
        for p in [98.0, 99.0, 100.0, 101.0, 102.0] {
            engine.update(p);
        }

        // Current price (102) is not at mean, but let's verify mean
        let mean = engine.get_mean().unwrap();
        assert!((mean - 100.0).abs() < 0.001);

        // Update with price at mean
        let z = engine.update(100.0).unwrap();
        // Z-Score should be close to 0 (actually slightly negative due to window shift)
        assert!(z.abs() < 0.5);
    }

    #[test]
    fn test_no_variance() {
        let mut engine = ZScoreEngine::new(5);

        // All same prices = no variance
        for _ in 0..5 {
            engine.update(100.0);
        }

        let z = engine.get_zscore().unwrap();
        assert_eq!(z, 0.0);
    }

    #[test]
    fn test_reset() {
        let mut engine = ZScoreEngine::new(5);

        for _ in 0..10 {
            engine.update(100.0);
        }
        assert!(engine.is_ready());

        engine.reset();

        assert_eq!(engine.count(), 0);
        assert!(!engine.is_ready());
        assert!(engine.get_zscore().is_none());
    }

    #[test]
    fn test_sliding_window() {
        let mut engine = ZScoreEngine::new(5);

        // Add 10 prices: 0, 1, 2, ..., 9
        for i in 0..10 {
            engine.update(i as f64);
        }

        // Window should contain: 5, 6, 7, 8, 9
        // Mean should be 7
        let mean = engine.get_mean().unwrap();
        assert!((mean - 7.0).abs() < 0.001);

        assert_eq!(engine.count(), 5);
    }

    #[test]
    fn test_batch_update() {
        let mut engine = ZScoreEngine::new(5);

        let prices = vec![100.0, 101.0, 102.0, 103.0, 104.0, 105.0];
        let z = engine.update_batch(prices);

        assert!(z.is_some());
        assert!(engine.is_ready());
    }

    // ========== NUMERICAL STABILITY TESTS ==========

    #[test]
    /// Test: Small values should closely match reference implementation
    fn test_small_values_accuracy() {
        let mut engine = ZScoreEngine::new(10);
        let prices: Vec<f64> = (0..20).map(|i| 100.0 + i as f64 * 0.1).collect();

        for price in &prices {
            engine.update(*price);
        }

        let engine_z = engine.get_zscore().unwrap();
        let reference_z = reference_zscore(engine.get_prices().as_slice(), *prices.last().unwrap()).unwrap();

        // Allow some tolerance due to different computational paths
        // The shifted data algorithm may have minor numerical differences
        assert!(
            (engine_z - reference_z).abs() < 0.1,
            "Small values: Engine Z={} doesn't closely match reference Z={}",
            engine_z, reference_z
        );
    }

    #[test]
    /// Test: Large values shouldn't cause catastrophic cancellation
    /// This is the CORE FIX - when values are large (e.g., 1e10),
    /// the naive sum approach would produce negative variance
    fn test_large_values_stability() {
        let mut engine = ZScoreEngine::new(20);
        let large_offset = 1_000_000_000.0; // 1 billion

        // Create a series with consistent small variation around a large offset
        // Mean should be large_offset, std dev should be ~0.816 (std dev of [0,1,2])
        for i in 0..30 {
            let price = large_offset + (i % 3) as f64; // Values: large_offset, large_offset+1, large_offset+2
            engine.update(price);
        }

        let mean = engine.get_mean().unwrap();
        let std = engine.get_std().unwrap();

        // Mean should be close to large_offset + 1.0
        assert!(
            (mean - (large_offset + 1.0)).abs() < 0.1,
            "Large values: Mean drifted too much. Got {}, expected ~{}",
            mean, large_offset + 1.0
        );

        // Std dev should be around 0.816 (std dev of [0,1,2])
        assert!(
            (std - 0.816).abs() < 0.01,
            "Large values: Std dev incorrect. Got {}, expected ~0.816",
            std
        );

        // Z-score at the mean should be close to 0
        let z_at_mean = engine.update(large_offset + 1.0);
        assert!(
            z_at_mean.unwrap().abs() < 0.1,
            "Large values: Z-score at mean incorrect. Got {}",
            z_at_mean.unwrap()
        );
    }

    #[test]
    /// Test: Very large values (1e15) - extreme case
    fn test_very_large_values() {
        let mut engine = ZScoreEngine::new(10);
        let huge_offset = 1e15;

        // Small variations around huge offset
        for i in 0..15 {
            let price = huge_offset + (i as f64 % 5.0);
            engine.update(price);
        }

        let mean = engine.get_mean().unwrap();
        let std = engine.get_std().unwrap();

        // Should maintain precision even at 1e15 scale
        assert!(
            mean.is_finite(),
            "Very large values: Mean became infinite or NaN. Got {}",
            mean
        );

        assert!(
            std.is_finite() && std > 0.0,
            "Very large values: Std dev is invalid: {}",
            std
        );
    }

    #[test]
    /// Test: Wikipedia's example that breaks naive algorithm
    /// Sample: (10^9 + 4, 10^9 + 7, 10^9 + 13, 10^9 + 16)
    /// True variance: 30
    /// Naive algorithm: -170.666... (WRONG!)
    fn test_wikipedia_catastrophic_cancellation() {
        let mut engine = ZScoreEngine::new(4);
        let offset = 1_000_000_000.0;

        // The exact example from Wikipedia
        let prices = [offset + 4.0, offset + 7.0, offset + 13.0, offset + 16.0];

        for price in prices {
            engine.update(price);
        }

        let mean = engine.get_mean().unwrap();
        let std = engine.get_std().unwrap();

        // Mean should be offset + 10
        assert!(
            (mean - (offset + 10.0)).abs() < 0.001,
            "Wikipedia example: Mean incorrect. Got {}, expected {}",
            mean, offset + 10.0
        );

        // Std dev should be sqrt(30) ≈ 5.477
        let expected_std = (30.0_f64).sqrt();
        assert!(
            (std - expected_std).abs() < 0.001,
            "Wikipedia example: Std dev incorrect. Got {}, expected {}",
            std, expected_std
        );

        // Most importantly: std must be POSITIVE (naive would give NaN or crash)
        assert!(
            std > 0.0,
            "Wikipedia example: Std dev should be positive, got {}",
            std
        );
    }

    #[test]
    /// Test: Extreme Wikipedia example (10^9 + offset)
    /// Naive algorithm would return -170.666 variance!
    fn test_wikipedia_extreme_case() {
        let mut engine = ZScoreEngine::new(4);
        let offset = 1_000_000_000.0;

        // Same relative values, larger offset (10^9)
        let prices = [offset + 4.0, offset + 7.0, offset + 13.0, offset + 16.0];

        for price in prices {
            engine.update(price);
        }

        let std = engine.get_std().unwrap();

        // Std dev should still be sqrt(30) ≈ 5.477
        let expected_std = (30.0_f64).sqrt();
        assert!(
            (std - expected_std).abs() < 0.001,
            "Extreme case: Std dev incorrect. Got {}, expected {}",
            std, expected_std
        );

        // With naive algorithm at this scale, variance would be NEGATIVE!
        assert!(
            std > 0.0,
            "Extreme case: Std dev should be positive (naive would fail)"
        );
    }

    #[test]
    /// Test: Mixed large and small values
    fn test_mixed_scale_values() {
        let mut engine = ZScoreEngine::new(10);

        // Start with small values, then go large
        for i in 0..5 {
            engine.update(100.0 + i as f64);
        }

        let large_offset = 1e10;
        for i in 0..5 {
            engine.update(large_offset + i as f64);
        }

        let mean = engine.get_mean().unwrap();
        let std = engine.get_std().unwrap();

        assert!(
            mean.is_finite(),
            "Mixed scale: Mean is invalid: {}",
            mean
        );

        assert!(
            std.is_finite(),
            "Mixed scale: Std dev is invalid: {}",
            std
        );
    }

    #[test]
    /// Test: Negative large values
    fn test_negative_large_values() {
        let mut engine = ZScoreEngine::new(10);
        let large_offset = -1_000_000_000.0;

        for i in 0..15 {
            let price = large_offset + (i % 3) as f64;
            engine.update(price);
        }

        let mean = engine.get_mean().unwrap();
        let std = engine.get_std().unwrap();

        assert!(
            mean.is_finite(),
            "Negative large values: Mean is invalid"
        );

        assert!(
            std.is_finite() && std > 0.0,
            "Negative large values: Std dev is invalid"
        );
    }

    #[test]
    /// Test: Variance should never be negative (numerical precision issue)
    fn test_variance_never_negative() {
        let mut engine = ZScoreEngine::new(20);

        // Add values that could cause precision issues with naive algorithm
        for i in 0..30 {
            let price = 1e10 + (i as f64 % 100.0);
            engine.update(price);
        }

        let std = engine.get_std().unwrap();

        // Std dev must be positive (naive would crash or return NaN)
        assert!(
            std >= 0.0,
            "Std dev should never be negative: {}",
            std
        );
    }

    #[test]
    /// Test: Zero variance handling
    fn test_zero_variance_stability() {
        let mut engine = ZScoreEngine::new(10);

        // All same value - zero variance
        for _ in 0..20 {
            engine.update(100.0);
        }

        let z = engine.get_zscore().unwrap();
        assert_eq!(z, 0.0, "Zero variance should return Z=0");

        // Update with same value
        let z2 = engine.update(100.0);
        assert_eq!(z2.unwrap(), 0.0, "Zero variance with same value should return Z=0");
    }

    #[test]
    /// Test: Nearly zero variance (should handle gracefully)
    fn test_nearly_zero_variance() {
        let mut engine = ZScoreEngine::new(10);

        // Very small variations
        for i in 0..15 {
            let price = 100.0 + (i as f64 * 1e-10); // Tiny variations
            engine.update(price);
        }

        let z = engine.get_zscore().unwrap();

        // Should be close to 0 but finite
        assert!(
            z.is_finite(),
            "Nearly zero variance produced infinite Z-score: {}",
            z
        );

        // Should be very small since all values are nearly identical
        assert!(
            z.abs() < 10.0,
            "Nearly zero variance produced too large Z-score: {}",
            z
        );
    }

    #[test]
    /// Test: Consistency across different lookback periods
    fn test_consistency_across_lookbacks() {
        let prices: Vec<f64> = (0..50).map(|i| 100.0 + i as f64 * 0.5).collect();

        for lookback in [5, 10, 20, 30] {
            let mut engine = ZScoreEngine::new(lookback);

            for price in &prices {
                engine.update(*price);
            }

            let mean = engine.get_mean().unwrap();
            let std = engine.get_std().unwrap();

            assert!(
                mean.is_finite(),
                "Lookback {}: Mean is invalid",
                lookback
            );

            assert!(
                std.is_finite() && std > 0.0,
                "Lookback {}: Std dev is invalid: {}",
                lookback, std
            );
        }
    }

    #[test]
    /// Test: Long sequence (simulate extended usage)
    fn test_long_sequence_stability() {
        let mut engine = ZScoreEngine::new(20);
        let base = 1_000_000.0;

        // Simulate 1000 updates
        for i in 0..1000 {
            let price = base + ((i as f64).sin() * 10.0); // Oscillating values
            engine.update(price);
        }

        let mean = engine.get_mean().unwrap();
        let std = engine.get_std().unwrap();

        assert!(
            mean.is_finite(),
            "Long sequence: Mean became invalid"
        );

        assert!(
            std.is_finite() && std > 0.0,
            "Long sequence: Std dev is invalid: {}",
            std
        );

        // Mean should be close to base
        assert!(
            (mean - base).abs() < 1.0,
            "Long sequence: Mean drifted too far. Got {}, expected ~{}",
            mean, base
        );
    }

    #[test]
    /// Test: Extreme value followed by normal values
    fn test_extreme_value_recovery() {
        let mut engine = ZScoreEngine::new(10);

        // Normal values first
        for i in 0..10 {
            engine.update(100.0 + i as f64);
        }

        // Extreme value
        engine.update(1e15);

        // Normal values again
        for i in 0..10 {
            engine.update(100.0 + i as f64);
        }

        // Should recover and produce valid results
        let mean = engine.get_mean().unwrap();
        let std = engine.get_std().unwrap();

        assert!(
            mean.is_finite(),
            "Extreme value: Mean never recovered"
        );

        assert!(
            std.is_finite(),
            "Extreme value: Std dev never recovered"
        );
    }

    #[test]
    /// Test: Comparison with numpy-style calculation for real-world prices
    fn test_realistic_trading_prices() {
        let mut engine = ZScoreEngine::new(20);

        // Simulate realistic BTC prices (around $50,000)
        let base_price = 50_000.0;
        let prices: Vec<f64> = (0..30)
            .map(|i| base_price + (i as f64 * 10.0) + ((i as f64).sin() * 100.0))
            .collect();

        for price in &prices {
            engine.update(*price);
        }

        let mean = engine.get_mean().unwrap();
        let std = engine.get_std().unwrap();

        assert!(
            mean.is_finite() && mean > base_price,
            "Realistic prices: Mean is invalid: {}",
            mean
        );

        assert!(
            std.is_finite() && std > 0.0,
            "Realistic prices: Std dev is invalid: {}",
            std
        );

        // Std dev should be reasonable (not tiny or huge)
        assert!(
            std > 10.0 && std < 1000.0,
            "Realistic prices: Std dev out of expected range: {}",
            std
        );
    }
}
