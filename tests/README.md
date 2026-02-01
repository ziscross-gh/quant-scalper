# Test Suite

Comprehensive test suite for the Quant Scalper Trading Bot.

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures and test utilities
├── unit/                    # Unit tests for individual modules
│   ├── test_config.py       # Configuration validation
│   ├── test_signals.py      # Signal generation logic
│   ├── test_circuit_breaker.py  # Risk management
│   ├── test_timezone.py     # Timezone handling
│   ├── test_database.py     # Database operations
│   └── test_backtest.py     # Backtesting engine
├── integration/             # Integration tests
│   └── test_engine.py       # Full trading workflow
├── test_circuit_breaker.py  # Legacy standalone test
└── test_engine.py           # Legacy integration test
```

## Running Tests

### Install Test Dependencies

```bash
pip install -r requirements-test.txt
```

### Run All Tests

```bash
pytest
```

### Run Specific Test Categories

```bash
# Unit tests only
pytest tests/unit/

# Integration tests only
pytest tests/integration/

# Specific test file
pytest tests/unit/test_config.py

# Specific test class
pytest tests/unit/test_config.py::TestConfig

# Specific test function
pytest tests/unit/test_config.py::TestConfig::test_load_from_dict
```

### Run with Coverage

```bash
# Generate coverage report
pytest --cov=bot --cov-report=html

# View HTML report
open htmlcov/index.html
```

### Run in Parallel

```bash
# Use multiple CPUs for faster execution
pytest -n auto
```

### Run with Verbose Output

```bash
pytest -v
```

### Run Only Fast Tests

```bash
# Skip slow tests
pytest -m "not slow"
```

### Run with Specific Markers

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run tests requiring Rust components
pytest -m requires_rust
```

## Test Markers

Tests are marked with the following categories:

- `unit`: Unit tests for individual components
- `integration`: Integration tests for full workflows
- `slow`: Tests that take a long time to run
- `requires_rust`: Tests that require Rust components to be built
- `requires_ibkr`: Tests that require IBKR connection
- `asyncio`: Tests that use async/await

## Writing Tests

### Test Naming Convention

- Test files: `test_*.py`
- Test classes: `Test*`
- Test functions: `test_*`

### Example Unit Test

```python
import pytest
from bot.config import Config

class TestConfig:
    def test_load_from_dict(self, sample_config_dict):
        """Test loading config from dictionary"""
        config = Config.from_dict(sample_config_dict)
        
        assert config.trading.symbol == "MES"
        assert config.risk.max_daily_loss == 500.0
```

### Example Integration Test

```python
import pytest

class TestTradingEngine:
    @pytest.mark.asyncio
    async def test_full_workflow(self, engine):
        """Test complete trading workflow"""
        await engine.start()
        
        # Process bars
        for bar in sample_bars:
            await engine.process_bar(bar)
        
        status = engine.get_status()
        assert status["running"] is True
        
        await engine.stop()
```

### Using Fixtures

Fixtures are defined in `conftest.py` and are automatically available to all tests:

```python
def test_with_fixtures(sample_config, temp_dir, mock_zscore_engine):
    """Test using shared fixtures"""
    engine = mock_zscore_engine(lookback=20)
    # ... test code
```

## Coverage Goals

Target coverage levels:

- **Overall**: 80%+
- **Core modules** (engine, signals, risk): 90%+
- **Utilities**: 70%+
- **Integration tests**: At least one end-to-end test per major feature

## Continuous Integration

Tests run automatically on:

- Every commit to `main` branch
- Every pull request
- Nightly builds

CI configuration: `.github/workflows/test.yml` (if using GitHub Actions)

## Troubleshooting

### Rust Tests Failing

Build the Rust components first:

```bash
cd rust
cargo test
maturin develop --release
cd ..
pytest
```

### Database Locked Errors

Tests use temporary databases. If you see "database is locked" errors:

```bash
# Clean up any stale test databases
find . -name "test_*.db" -delete
```

### Async Test Warnings

Make sure `pytest-asyncio` is installed:

```bash
pip install pytest-asyncio
```

### Import Errors

Ensure the project root is in PYTHONPATH:

```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest
```

## Best Practices

1. **One assertion per test** (when possible)
2. **Use descriptive test names**
3. **Test edge cases and error conditions**
4. **Mock external dependencies** (IBKR, Telegram)
5. **Use fixtures for common setup**
6. **Keep tests fast** (mock slow operations)
7. **Test behavior, not implementation**
8. **Maintain test independence** (no shared state between tests)

## Performance

Current test suite performance:

- **Unit tests**: ~10 seconds
- **Integration tests**: ~30 seconds  
- **Total**: ~40 seconds
- **Parallel execution**: ~15 seconds (with `-n auto`)

## Future Enhancements

- [ ] Property-based testing with Hypothesis
- [ ] Mutation testing with mutpy
- [ ] Load testing for backtest engine
- [ ] End-to-end tests with real IBKR paper account
- [ ] Performance regression tests
- [ ] Visual regression tests for dashboard
