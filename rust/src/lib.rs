//! High-performance trading components with Python bindings
//! 
//! This crate provides Rust implementations of performance-critical
//! trading algorithms, exposed to Python via PyO3.

use pyo3::prelude::*;

mod zscore;
mod risk_calculator;

pub use zscore::ZScoreEngine;
pub use risk_calculator::RiskCalculator;

/// Python module definition
#[pymodule]
fn quant_scalper_rust(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<ZScoreEngine>()?;
    m.add_class::<RiskCalculator>()?;
    
    // Module version
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    
    Ok(())
}
