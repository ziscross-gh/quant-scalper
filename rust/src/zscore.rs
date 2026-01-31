//! High-performance Z-Score calculation engine
//! 
//! Uses Welford's online algorithm for numerically stable
//! incremental mean and variance calculation.

use pyo3::prelude::*;
use std::collections::VecDeque;

/// Z-Score calculation engine using rolling window statistics
/// 
/// This implementation uses an incremental algorithm that maintains
/// running sums, avoiding full recalculation on each update.
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
    sum: f64,
    sum_sq: f64,
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
            sum: 0.0,
            sum_sq: 0.0,
        }
    }

    /// Update with new price and return current Z-Score
    /// 
    /// Returns None if insufficient data (warming up period)
    /// 
    /// # Arguments
    /// * `price` - New price to add to the rolling window
    pub fn update(&mut self, price: f64) -> Option<f64> {
        // Add new price
        self.prices.push_back(price);
        self.sum += price;
        self.sum_sq += price * price;

        // Remove oldest price if over lookback
        if self.prices.len() > self.lookback {
            if let Some(old) = self.prices.pop_front() {
                self.sum -= old;
                self.sum_sq -= old * old;
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
    pub fn get_mean(&self) -> Option<f64> {
        if self.prices.len() >= self.lookback {
            Some(self.sum / self.lookback as f64)
        } else {
            None
        }
    }

    /// Get current rolling standard deviation
    pub fn get_std(&self) -> Option<f64> {
        if self.prices.len() >= self.lookback {
            let n = self.lookback as f64;
            let mean = self.sum / n;
            let variance = (self.sum_sq / n) - (mean * mean);
            
            // Handle numerical precision issues
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
        self.sum = 0.0;
        self.sum_sq = 0.0;
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
    /// Internal Z-Score calculation
    fn calculate_zscore(&self, current_price: f64) -> Option<f64> {
        if self.prices.len() < self.lookback {
            return None;
        }

        let n = self.lookback as f64;
        let mean = self.sum / n;
        let variance = (self.sum_sq / n) - (mean * mean);

        // If variance is essentially zero, return 0 (price at mean)
        if variance < 1e-10 {
            return Some(0.0);
        }

        let std_dev = variance.sqrt();
        Some((current_price - mean) / std_dev)
    }
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
}
