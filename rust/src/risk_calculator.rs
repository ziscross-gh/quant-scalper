//! Real-time risk calculation engine
//! 
//! Tracks positions and calculates P&L with minimal latency.

use pyo3::prelude::*;
use std::collections::HashMap;

/// Position data
#[derive(Clone, Debug)]
struct Position {
    symbol: String,
    quantity: i32,
    entry_price: f64,
    current_price: f64,
    multiplier: f64,
}

impl Position {
    fn unrealized_pnl(&self) -> f64 {
        let price_diff = self.current_price - self.entry_price;
        price_diff * self.quantity as f64 * self.multiplier
    }
}

/// Real-time risk calculator
/// 
/// Tracks positions and calculates P&L metrics with O(1) updates.
/// 
/// # Example (Python)
/// ```python
/// from quant_scalper_rust import RiskCalculator
/// 
/// calc = RiskCalculator(500.0)  # $500 daily loss limit
/// 
/// # Add position
/// calc.update_position("MES", 1, 5120.50, 5.0)  # Long 1 MES @ 5120.50
/// 
/// # Update price
/// calc.update_price("MES", 5125.00)
/// 
/// # Check P&L
/// print(f"Unrealized P&L: ${calc.unrealized_pnl():.2f}")
/// ```
#[pyclass]
pub struct RiskCalculator {
    positions: HashMap<String, Position>,
    max_daily_loss: f64,
    realized_pnl: f64,
}

#[pymethods]
impl RiskCalculator {
    /// Create new risk calculator with daily loss limit
    /// 
    /// # Arguments
    /// * `max_daily_loss` - Maximum loss allowed before circuit breaker (positive number)
    #[new]
    pub fn new(max_daily_loss: f64) -> Self {
        Self {
            positions: HashMap::new(),
            max_daily_loss: max_daily_loss.abs(),
            realized_pnl: 0.0,
        }
    }

    /// Add or update a position
    /// 
    /// # Arguments
    /// * `symbol` - Instrument symbol (e.g., "MES")
    /// * `quantity` - Position size (positive=long, negative=short, 0=remove)
    /// * `entry_price` - Average entry price
    /// * `multiplier` - Contract multiplier (e.g., 5 for MES)
    pub fn update_position(
        &mut self,
        symbol: String,
        quantity: i32,
        entry_price: f64,
        multiplier: f64,
    ) {
        if quantity == 0 {
            self.positions.remove(&symbol);
        } else {
            let current_price = self
                .positions
                .get(&symbol)
                .map(|p| p.current_price)
                .unwrap_or(entry_price);

            self.positions.insert(
                symbol.clone(),
                Position {
                    symbol,
                    quantity,
                    entry_price,
                    current_price,
                    multiplier,
                },
            );
        }
    }

    /// Update current market price for a position
    /// 
    /// # Arguments
    /// * `symbol` - Instrument symbol
    /// * `price` - Current market price
    pub fn update_price(&mut self, symbol: &str, price: f64) {
        if let Some(pos) = self.positions.get_mut(symbol) {
            pos.current_price = price;
        }
    }

    /// Add realized P&L from a closed trade
    /// 
    /// # Arguments
    /// * `pnl` - Realized profit/loss amount
    pub fn add_realized_pnl(&mut self, pnl: f64) {
        self.realized_pnl += pnl;
    }

    /// Get total unrealized P&L across all positions
    pub fn unrealized_pnl(&self) -> f64 {
        self.positions.values().map(|p| p.unrealized_pnl()).sum()
    }

    /// Get realized P&L for the day
    pub fn get_realized_pnl(&self) -> f64 {
        self.realized_pnl
    }

    /// Get total P&L (realized + unrealized)
    pub fn total_pnl(&self) -> f64 {
        self.realized_pnl + self.unrealized_pnl()
    }

    /// Check if daily loss limit is breached
    pub fn is_daily_loss_breached(&self) -> bool {
        self.total_pnl() <= -self.max_daily_loss
    }

    /// Get remaining risk budget before circuit breaker
    pub fn remaining_risk(&self) -> f64 {
        self.max_daily_loss + self.total_pnl()
    }

    /// Get number of open positions
    pub fn position_count(&self) -> usize {
        self.positions.len()
    }

    /// Check if a specific position exists
    pub fn has_position(&self, symbol: &str) -> bool {
        self.positions.contains_key(symbol)
    }

    /// Get position quantity for a symbol (0 if no position)
    pub fn get_quantity(&self, symbol: &str) -> i32 {
        self.positions.get(symbol).map(|p| p.quantity).unwrap_or(0)
    }

    /// Get position details as a list of dicts
    pub fn get_positions(&self, py: Python) -> PyResult<Vec<PyObject>> {
        let mut result = Vec::new();
        
        for pos in self.positions.values() {
            let dict = pyo3::types::PyDict::new(py);
            dict.set_item("symbol", &pos.symbol)?;
            dict.set_item("quantity", pos.quantity)?;
            dict.set_item("entry_price", pos.entry_price)?;
            dict.set_item("current_price", pos.current_price)?;
            dict.set_item("multiplier", pos.multiplier)?;
            dict.set_item("unrealized_pnl", pos.unrealized_pnl())?;
            result.push(dict.into());
        }
        
        Ok(result)
    }

    /// Reset for new trading day
    pub fn reset_daily(&mut self) {
        self.realized_pnl = 0.0;
        // Note: positions are NOT cleared - they carry over
    }

    /// Clear all positions (for emergency flatten)
    pub fn clear_positions(&mut self) {
        self.positions.clear();
    }

    /// Get the daily loss limit
    pub fn get_max_daily_loss(&self) -> f64 {
        self.max_daily_loss
    }

    /// Update the daily loss limit
    pub fn set_max_daily_loss(&mut self, limit: f64) {
        self.max_daily_loss = limit.abs();
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_new_calculator() {
        let calc = RiskCalculator::new(500.0);
        assert_eq!(calc.position_count(), 0);
        assert_eq!(calc.total_pnl(), 0.0);
        assert!(!calc.is_daily_loss_breached());
    }

    #[test]
    fn test_add_position() {
        let mut calc = RiskCalculator::new(500.0);
        
        calc.update_position("MES".to_string(), 1, 5000.0, 5.0);
        
        assert_eq!(calc.position_count(), 1);
        assert!(calc.has_position("MES"));
        assert_eq!(calc.get_quantity("MES"), 1);
    }

    #[test]
    fn test_unrealized_pnl_long() {
        let mut calc = RiskCalculator::new(500.0);
        
        // Long 1 MES @ 5000
        calc.update_position("MES".to_string(), 1, 5000.0, 5.0);
        
        // Price moves to 5010 (+10 points * $5 = +$50)
        calc.update_price("MES", 5010.0);
        
        assert!((calc.unrealized_pnl() - 50.0).abs() < 0.01);
    }

    #[test]
    fn test_unrealized_pnl_short() {
        let mut calc = RiskCalculator::new(500.0);
        
        // Short 1 MES @ 5000
        calc.update_position("MES".to_string(), -1, 5000.0, 5.0);
        
        // Price moves to 4990 (-10 points * -1 * $5 = +$50)
        calc.update_price("MES", 4990.0);
        
        assert!((calc.unrealized_pnl() - 50.0).abs() < 0.01);
    }

    #[test]
    fn test_daily_loss_limit() {
        let mut calc = RiskCalculator::new(500.0);
        
        // Add losing trade
        calc.add_realized_pnl(-300.0);
        assert!(!calc.is_daily_loss_breached());
        assert_eq!(calc.remaining_risk(), 200.0);
        
        // Add another losing trade
        calc.add_realized_pnl(-250.0);
        assert!(calc.is_daily_loss_breached());
    }

    #[test]
    fn test_remove_position() {
        let mut calc = RiskCalculator::new(500.0);
        
        calc.update_position("MES".to_string(), 1, 5000.0, 5.0);
        assert!(calc.has_position("MES"));
        
        // Setting quantity to 0 removes position
        calc.update_position("MES".to_string(), 0, 0.0, 0.0);
        assert!(!calc.has_position("MES"));
    }

    #[test]
    fn test_reset_daily() {
        let mut calc = RiskCalculator::new(500.0);
        
        calc.update_position("MES".to_string(), 1, 5000.0, 5.0);
        calc.add_realized_pnl(-100.0);
        
        calc.reset_daily();
        
        // Realized P&L resets
        assert_eq!(calc.get_realized_pnl(), 0.0);
        
        // Position remains
        assert!(calc.has_position("MES"));
    }
}
