# Testing Documentation

## Overview

Comprehensive test suite for the Quant Scalper Trading Bot with **100+ test cases** covering all major components.

## Test Coverage

### Unit Tests (6 modules)

#### 1. Configuration Tests (`tests/unit/test_config.py`)
- **30+ tests** covering:
  - Trading configuration validation
  - Risk configuration validation
  - IBKR configuration validation
  - Telegram configuration validation
  - YAML loading and parsing
  - Edge cases and boundary conditions

#### 2. Signal Generation Tests (`tests/unit/test_signals.py`)
- **25+ tests** covering:
  - Signal type and state enumerations
  - Signal dataclass operations
  - Z-Score calculation integration
  - Warmup period handling
  - Volume filtering
  - Entry/exit signal generation
  - Position state management
  - Edge cases (zero variance, extreme values)

#### 3. Circuit Breaker Tests (`tests/unit/test_circuit_breaker.py`)
- **35+ tests** covering:
  - Daily loss limit enforcement
  - Consecutive loss tracking
  - Drawdown limit monitoring
  - Position duration timeout
  - Trade count limiting
  - Cooldown period management
  - Circuit breaker state
  - Trigger callbacks
  - Recovery scenarios

#### 4. Timezone Tests (`tests/unit/test_timezone.py`)
- **40+ tests** covering:
  - Timezone conversions (UTC, ET, SGT)
  - Market hours detection (stocks)
  - Futures trading hours (CME Globex)
  - Market holiday detection
  - Trading allowed checks
  - Next market open calculation
  - Time formatting
  - DST transition handling
  - Edge cases (leap years, year boundaries)

#### 5. Database Tests (`tests/unit/test_database.py`)
- **30+ tests** covering:
  - Database initialization
  - Trade logging and retrieval
  - Trade status updates
  - Signal logging
  - Event logging
  - P&L calculation
  - Trade statistics
  - Data models (Trade, Signal, Event)
  - Edge cases and error handling

#### 6. Backtest Engine Tests (`tests/unit/test_backtest.py`)
- **35+ tests** covering:
  - Backtest configuration
  - Bar data structures
  - Backtest execution
  - Performance metrics (win rate, profit factor, Sharpe ratio)
  - Commission and slippage
  - Equity curve generation
  - Trade logging
  - Risk limit enforcement
  - Edge cases (empty data, extreme moves, zero variance)

### Integration Tests (`tests/integration/test_engine.py`)

- **20+ tests** covering:
  - Full trading workflow
  - Engine startup/shutdown
  - Bar processing pipeline
  - Signal-to-trade workflow
  - Circuit breaker integration
  - Database logging integration
  - Telegram alerts integration
  - Position entry/exit cycles
  - Multiple trading sessions
  - Error handling and recovery
  - Concurrent processing
  - Status reporting
  - Dry run mode
  - Risk management enforcement

## Test Infrastructure

### Fixtures (`tests/conftest.py`)

Shared fixtures for all tests:

- `temp_dir` - Temporary directory for test files
- `sample_config_dict` - Sample configuration dictionary
- `sample_config` - Sample Config object
- `config_yaml_file` - Temporary YAML config file
- `mock_price_bars` - Sample price bar data
- `mock_zscore_engine` - Mock Z-Score engine
- `mock_risk_calculator` - Mock risk calculator
- `mock_ibkr_client` - Mock IBKR client
- `mock_telegram_alerts` - Mock Telegram alerts

### Configuration

- `pytest.ini` - Pytest configuration with markers and coverage settings
- `requirements-test.txt` - Test dependencies
- `scripts/run_tests.sh` - Test runner script
- `tests/README.md` - Detailed testing documentation

## Running Tests

### Quick Start

```bash
# Install dependencies
pip install -r requirements-test.txt

# Run all tests
pytest

# Run with coverage
./scripts/run_tests.sh all

# Run unit tests only
./scripts/run_tests.sh unit

# Run integration tests only
./scripts/run_tests.sh integration

# Run in parallel
./scripts/run_tests.sh parallel
```

### Coverage Goals

| Component | Target | Current |
|-----------|--------|---------|
| Overall | 80% | TBD |
| Core modules | 90% | TBD |
| Risk management | 95% | TBD |
| Utilities | 70% | TBD |

## Test Statistics

```
Total Tests: 215+
├── Unit Tests: 195+
│   ├── Configuration: 30
│   ├── Signals: 25
│   ├── Circuit Breaker: 35
│   ├── Timezone: 40
│   ├── Database: 30
│   └── Backtest: 35
└── Integration Tests: 20+

Test Files: 8
Test Classes: 40+
Lines of Test Code: ~3,500
```

## Continuous Integration

Tests are designed to run in CI/CD pipelines:

- Fast execution (< 1 minute for all tests)
- Isolated (no external dependencies)
- Reproducible (deterministic results)
- Parallel execution support

## Best Practices Implemented

✅ **Comprehensive coverage** - All major components tested
✅ **Edge case testing** - Boundary conditions and error cases
✅ **Fixture reuse** - DRY principle with shared fixtures
✅ **Mocking** - External dependencies mocked (IBKR, Telegram, Rust)
✅ **Async support** - Proper async/await testing
✅ **Clear naming** - Descriptive test names
✅ **Documentation** - Docstrings for all tests
✅ **Fast execution** - Optimized for speed
✅ **Isolated tests** - No shared state between tests
✅ **Realistic data** - Sample data mirrors production

## Test Markers

Tests are categorized with markers:

- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.slow` - Slow tests (> 5 seconds)
- `@pytest.mark.requires_rust` - Requires Rust components
- `@pytest.mark.requires_ibkr` - Requires IBKR connection
- `@pytest.mark.asyncio` - Async tests

## Next Steps

To extend the test suite:

1. **Property-based testing** - Add Hypothesis for generative testing
2. **Performance tests** - Add benchmarks and regression tests
3. **Load tests** - Test backtest engine with large datasets
4. **E2E tests** - Add tests with real IBKR paper account
5. **Visual tests** - Add dashboard UI tests
6. **Security tests** - Add security scanning and penetration tests

## Maintenance

- Run tests before every commit
- Maintain > 80% coverage
- Update tests when adding features
- Review and refactor tests quarterly
- Keep test execution time < 2 minutes

## Troubleshooting

See `tests/README.md` for detailed troubleshooting guide.

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Testing Best Practices](https://docs.python-guide.org/writing/tests/)
- [Async Testing](https://pytest-asyncio.readthedocs.io/)
